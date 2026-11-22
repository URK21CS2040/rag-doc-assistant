import re
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
import chromadb
from chromadb.config import Settings as ChromaSettings

# Silence broken PostHog telemetry in ChromaDB
import os
os.environ["ANONYMIZED_TELEMETRY"] = "False"
try:
    import posthog
    posthog.capture = lambda *args, **kwargs: None
except Exception:
    pass
try:
    import chromadb.telemetry.product.posthog as chroma_posthog
    chroma_posthog.Posthog.capture = lambda *args, **kwargs: None
    chroma_posthog.Posthog._direct_capture = lambda *args, **kwargs: None
except Exception:
    pass

try:
    from rank_bm25 import BM25Okapi
    HAS_BM25 = True
except ImportError:
    BM25Okapi = None
    HAS_BM25 = False
from app.config import settings
from app.domain.entities import DocumentChunk

logger = logging.getLogger(__name__)

TECHNICAL_SYNONYMS: Dict[str, List[str]] = {
    "voltage": ["voltage", "v", "dc", "supply"],
    "voltages": ["voltage", "v", "dc", "supply"],
    "processor": ["processor", "cpu", "arm", "core", "x86", "x86-64"],
    "processors": ["processor", "cpu", "arm", "core", "x86", "x86-64"],
    "cpu": ["cpu", "processor", "core", "architecture"],
    "ram": ["ram", "memory", "gb"],
    "memory": ["memory", "ram", "gb"],
    "storage": ["storage", "ssd", "disk", "gb"],
    "ssd": ["ssd", "storage", "industrial"],
    "network": ["network", "ethernet", "wifi", "wi-fi", "interface"],
    "ethernet": ["ethernet", "network", "interface", "lan"],
    "temperature": ["temperature", "deg", "c", "operating", "range"],
    "monitor": ["monitor", "monitored", "assets", "supported", "supervision"],
    "assets": ["assets", "asset", "monitored", "supported"],
    "frequency": ["frequency", "hz", "sampling", "samples"],
    "sampling": ["sampling", "rate", "frequency", "hz", "interval"],
    "algorithm": ["algorithm", "model", "isolation", "forest"],
    "model": ["model", "algorithm", "isolation", "forest", "classifier"],
    "threshold": ["threshold", "warning", "critical", "score", "alert"],
    "thresholds": ["threshold", "thresholds", "warning", "critical", "score", "alert"],
    "cache": ["cache", "offline", "buffer", "retention", "hours"],
    "pilot": ["pilot", "update", "rollout", "duration", "hours", "severity"],
}

def tokenize(text: str) -> List[str]:
    raw = [t for t in re.findall(r'[a-zA-Z0-9_\-\.]+', text.lower()) if len(t) > 1]
    expanded = list(raw)
    for t in raw:
        syns = TECHNICAL_SYNONYMS.get(t)
        if syns:
            expanded.extend(syns)
    seen = set()
    return [x for x in expanded if not (x in seen or seen.add(x))]

class ChromaVectorStore:
    def __init__(self, embeddings: Any, persist_directory: Optional[str] = None) -> None:
        self._embeddings = embeddings
        db_path = persist_directory or settings.chroma_persist_directory
        self._client = chromadb.PersistentClient(path=db_path, settings=ChromaSettings(anonymized_telemetry=False, is_persistent=True))

        model_name = getattr(embeddings, "model_name", getattr(embeddings, "model", "default_model"))
        dim = getattr(embeddings, "dim", 384)
        safe_model_name = re.sub(r'[^a-zA-Z0-9_-]', '_', model_name)
        collection_name = f"docs_{safe_model_name}"

        logger.info("Initializing Chroma collection: %s (model: %s, dim: %d)", collection_name, model_name, dim)
        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            metadata={
                "hnsw:space": "cosine",
                "embedding_model": str(model_name),
                "dimension": dim,
            }
        )

        # In-memory BM25 index components
        self._bm25_corpus_ids: List[str] = []
        self._bm25_corpus_docs: List[DocumentChunk] = []
        self._bm25_index: Optional[BM25Okapi] = None
        self._bm25_initialized = False

    def _ensure_bm25_initialized(self) -> None:
        if self._bm25_initialized:
            return
        try:
            total_count = self._collection.count()
            if total_count > 0:
                data = self._collection.get(include=["metadatas", "documents"])
                if data and data["ids"]:
                    docs = []
                    for i in range(len(data["ids"])):
                        chunk_id = data["ids"][i]
                        text = data["documents"][i]
                        meta = data["metadatas"][i] if data["metadatas"] else {}
                        source = meta.get("source", "unknown")
                        docs.append(DocumentChunk(
                            chunk_id=chunk_id,
                            document_id=source,
                            text=text,
                            metadata=meta,
                            score=0.0
                        ))
                    self._rebuild_bm25(docs)
        except Exception:
            logger.exception("Failed to initialize BM25 index from collection")
        self._bm25_initialized = True

    def _rebuild_bm25(self, docs: List[DocumentChunk]) -> None:
        self._bm25_corpus_docs = docs
        self._bm25_corpus_ids = [d.chunk_id for d in docs]
        tokenized_corpus = [tokenize(d.text) for d in docs]
        if HAS_BM25 and tokenized_corpus and any(len(t) > 0 for t in tokenized_corpus):
            self._bm25_index = BM25Okapi(tokenized_corpus)
        else:
            self._bm25_index = None

    def add_chunks(self, chunks: List[DocumentChunk]) -> None:
        if not chunks:
            return
        ids = [chunk.chunk_id for chunk in chunks]
        documents = [chunk.text for chunk in chunks]
        metadatas = [chunk.metadata for chunk in chunks]
        embeddings_list = self._embeddings.embed_documents(documents)

        self._collection.upsert(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings_list
        )

        self._ensure_bm25_initialized()
        # Merge new chunks into BM25 corpus and rebuild
        existing_map = {d.chunk_id: d for d in self._bm25_corpus_docs}
        for c in chunks:
            existing_map[c.chunk_id] = c
        self._rebuild_bm25(list(existing_map.values()))
        logger.info("Added %d chunks to Chroma and updated BM25 index", len(chunks))

    def delete_document(self, document_id: str) -> None:
        self._ensure_bm25_initialized()
        doc_id_clean = document_id.strip()
        target_bname = Path(doc_id_clean).name.lower()
        clean_ids = list(set([
            doc_id_clean,
            doc_id_clean.rstrip('/'),
            Path(doc_id_clean).name,
            f"/app/data/uploads/{Path(doc_id_clean).name}",
            f"./data/uploads/{Path(doc_id_clean).name}",
            f"data/uploads/{Path(doc_id_clean).name}",
            f"/app/data/sample_docs/{Path(doc_id_clean).name}",
            f"./data/sample_docs/{Path(doc_id_clean).name}",
            f"data/sample_docs/{Path(doc_id_clean).name}",
        ]))

        try:
            total_count = self._collection.count()
            if total_count > 0:
                data = self._collection.get(include=["metadatas"])
                matching_ids = []
                if data and data["ids"]:
                    for i, cid in enumerate(data["ids"]):
                        meta = data["metadatas"][i] if data["metadatas"] else {}
                        src = str(meta.get("source", "")).strip()
                        src_bname = Path(src).name.lower()
                        if (
                            src == doc_id_clean
                            or src.rstrip('/') == doc_id_clean.rstrip('/')
                            or (target_bname and src_bname == target_bname)
                            or src in clean_ids
                            or (target_bname and target_bname in src.lower())
                            or cid.startswith(doc_id_clean)
                        ):
                            matching_ids.append(cid)
                if matching_ids:
                    self._collection.delete(ids=matching_ids)
                    logger.info("Deleted %d chunks from Chroma for document '%s'", len(matching_ids), document_id)
                else:
                    self._collection.delete(where={"source": {"$in": clean_ids}})
        except Exception as e:
            logger.warning("Error deleting document %s from Chroma: %s", document_id, e)

        remaining = [
            d for d in self._bm25_corpus_docs
            if d.document_id != doc_id_clean
            and d.document_id.rstrip('/') != doc_id_clean.rstrip('/')
            and d.metadata.get("source") != doc_id_clean
            and (not target_bname or Path(d.document_id).name.lower() != target_bname)
            and (not target_bname or Path(d.metadata.get("source", "")).name.lower() != target_bname)
            and d.document_id not in clean_ids
        ]
        self._rebuild_bm25(remaining)
        logger.info("Deleted document %s from Chroma and BM25 index (remaining chunks: %d)", document_id, len(remaining))

    def delete_all_documents(self) -> int:
        self._ensure_bm25_initialized()
        total_deleted = 0
        try:
            total_count = self._collection.count()
            if total_count > 0:
                data = self._collection.get()
                if data and data["ids"]:
                    total_deleted = len(data["ids"])
                    self._collection.delete(ids=data["ids"])
            logger.info("Deleted all %d chunks from ChromaDB collection", total_deleted)
        except Exception as e:
            logger.exception("Error deleting all documents from Chroma: %s", e)

        self._rebuild_bm25([])
        return total_deleted

    def similarity_search(
        self,
        query: str,
        k: int = 8,
        document_ids: Optional[List[str]] = None
    ) -> List[DocumentChunk]:
        total_count = self._collection.count()
        if total_count == 0:
            return []

        self._ensure_bm25_initialized()

        # 1. Prepare Chroma where filter for scoped retrieval
        where_clause = None
        if document_ids:
            all_target_ids = []
            for d in document_ids:
                d_str = str(d).strip()
                if not d_str or d_str == "all":
                    continue
                bname = Path(d_str).name
                all_target_ids.extend([
                    d_str,
                    bname,
                    f"/app/data/uploads/{bname}",
                    f"/app/data/sample_docs/{bname}",
                    f"data/uploads/{bname}",
                    f"data/sample_docs/{bname}",
                    f"./data/uploads/{bname}",
                    f"./data/sample_docs/{bname}",
                ])
            all_target_ids = list(set(all_target_ids))
            if all_target_ids:
                if len(all_target_ids) == 1:
                    where_clause = {"source": all_target_ids[0]}
                else:
                    where_clause = {"source": {"$in": all_target_ids}}

        # 2. Chroma Dense Search
        dense_ranks: Dict[str, int] = {}
        dense_chunk_map: Dict[str, DocumentChunk] = {}
        try:
            query_embedding = self._embeddings.embed_query(query)
            n_fetch = min(max(k * 4, 12), total_count)
            query_kwargs: Dict[str, Any] = {
                "query_embeddings": [query_embedding],
                "n_results": n_fetch,
                "include": ["metadatas", "documents", "distances"],
            }
            if where_clause:
                query_kwargs["where"] = where_clause

            vector_res = self._collection.query(**query_kwargs)
            if vector_res and vector_res["ids"] and vector_res["ids"][0]:
                for rank, (cid, doc_text, meta, dist) in enumerate(
                    zip(
                        vector_res["ids"][0],
                        vector_res["documents"][0],
                        vector_res["metadatas"][0],
                        vector_res["distances"][0],
                    ),
                    start=1,
                ):
                    dense_ranks[cid] = rank
                    src = meta.get("source", "unknown") if meta else "unknown"
                    # Cosine distance to similarity
                    cos_sim = max(0.0, min(1.0, 1.0 - (dist / 2.0)))
                    dense_chunk_map[cid] = DocumentChunk(
                        chunk_id=cid,
                        document_id=src,
                        text=doc_text,
                        metadata=meta or {},
                        score=cos_sim,
                    )
        except Exception:
            logger.exception("Dense vector search failed")

        # 3. BM25 Lexical Search
        bm25_ranks: Dict[str, int] = {}
        bm25_chunk_map: Dict[str, DocumentChunk] = {}
        q_tokens = tokenize(query)

        if self._bm25_index and q_tokens:
            eligible_docs = self._bm25_corpus_docs
            if document_ids:
                clean_targets = set(
                    [str(d).strip() for d in document_ids if d and d != "all"]
                    + [str(d).strip().rstrip('/') for d in document_ids if d and d != "all"]
                    + [Path(str(d).strip()).name for d in document_ids if d and d != "all"]
                )
                if clean_targets:
                    eligible_docs = [
                        d for d in self._bm25_corpus_docs
                        if d.document_id in clean_targets
                        or d.document_id.rstrip('/') in clean_targets
                        or Path(d.document_id).name in clean_targets
                        or d.metadata.get("source") in clean_targets
                    ]

            if eligible_docs:
                eligible_chunk_ids = {d.chunk_id for d in eligible_docs}
                scores = self._bm25_index.get_scores(q_tokens)
                doc_score_pairs = []
                for idx, d in enumerate(self._bm25_corpus_docs):
                    if d.chunk_id in eligible_chunk_ids and scores[idx] > 0.0:
                        doc_score_pairs.append((scores[idx], d))

                doc_score_pairs.sort(key=lambda x: x[0], reverse=True)
                for rank, (s, d) in enumerate(doc_score_pairs[:k * 4], start=1):
                    bm25_ranks[d.chunk_id] = rank
                    bm25_chunk_map[d.chunk_id] = d

        # 4. Reciprocal Rank Fusion (RRF) with exact keyword boost and upload priority
        all_candidate_ids = set(dense_ranks.keys()).union(set(bm25_ranks.keys()))
        if not all_candidate_ids:
            return []

        stopwords = {
            'what', 'which', 'who', 'whom', 'whose', 'where', 'when', 'why', 'how',
            'does', 'do', 'did', 'done', 'doing',
            'is', 'are', 'was', 'were', 'be', 'been', 'being',
            'have', 'has', 'had', 'having',
            'can', 'could', 'shall', 'should', 'will', 'would', 'may', 'might', 'must',
            'tell', 'give', 'show', 'explain', 'describe', 'find', 'get', 'know', 'say',
            'about', 'with', 'from', 'into', 'onto', 'through', 'over', 'under', 'above', 'below',
            'for', 'and', 'nor', 'but', 'or', 'yet', 'so', 'the', 'a', 'an', 'this', 'that', 'these', 'those',
            'many', 'much', 'more', 'most', 'some', 'any', 'all', 'few', 'both', 'each', 'every',
            'between', 'difference', 'according', 'documentation', 'provided'
        }
        tech_query_words = [w for w in re.findall(r'[a-zA-Z0-9_\-\.]+', query.lower()) if len(w) > 2 and w not in stopwords]

        scored_candidates = []
        for cid in all_candidate_ids:
            chunk = dense_chunk_map.get(cid) or bm25_chunk_map.get(cid)
            if not chunk:
                continue

            rrf_score = 0.0
            if cid in dense_ranks:
                rrf_score += 1.5 / (60.0 + dense_ranks[cid])  # Prioritize dense semantic retrieval
            if cid in bm25_ranks:
                rrf_score += 1.0 / (60.0 + bm25_ranks[cid])

            # Prioritize uploaded documents over sample documents
            is_upload = "uploads" in chunk.document_id or "/uploads" in chunk.document_id
            if is_upload:
                rrf_score += 0.006

            # Exact keyword match bonus for technical keywords
            c_text_lower = chunk.text.lower()
            matched_kws = sum(1 for w in tech_query_words if w in c_text_lower)
            kw_ratio = (matched_kws / len(tech_query_words)) if tech_query_words else 0.0
            rrf_score += (kw_ratio * 0.010)

            # High-resolution normalized score preserving relative ranking
            normalized_score = round(min(1.0, rrf_score / 0.055), 4)

            cand_obj = DocumentChunk(
                chunk_id=chunk.chunk_id,
                document_id=chunk.document_id,
                text=chunk.text,
                metadata=chunk.metadata,
                score=normalized_score,
            )
            dense_rank = dense_ranks.get(cid, 999)
            bm25_rank = bm25_ranks.get(cid, 999)
            scored_candidates.append((rrf_score, -dense_rank, -bm25_rank, cand_obj))

        # Sort strictly by raw continuous RRF score, breaking any ties by dense rank and BM25 rank
        scored_candidates.sort(key=lambda x: (x[0], x[1], x[2]), reverse=True)
        top_candidates = [item[3] for item in scored_candidates[:k]]

        # 5. Two-phase candidate addition: Prioritize top scored candidates from all pages first
        final_chunks: List[DocumentChunk] = []
        seen_chunk_ids: Set[str] = set()

        for cand in top_candidates:
            if cand.chunk_id not in seen_chunk_ids:
                seen_chunk_ids.add(cand.chunk_id)
                final_chunks.append(cand)

        # Then expand immediate adjacent neighbors (abs(index_diff) == 1) on the same page if capacity allows
        if self._bm25_corpus_docs and len(final_chunks) < k:
            for cand in top_candidates:
                if len(final_chunks) >= k:
                    break
                cand_page = cand.metadata.get("page")
                cand_idx = cand.metadata.get("chunk_index")
                cand_bname = Path(cand.document_id).name
                if cand_page is not None and cand_idx is not None:
                    for neighbor in self._bm25_corpus_docs:
                        if len(final_chunks) >= k:
                            break
                        n_page = neighbor.metadata.get("page")
                        n_idx = neighbor.metadata.get("chunk_index")
                        n_bname = Path(neighbor.document_id).name
                        if (
                            neighbor.chunk_id not in seen_chunk_ids
                            and n_bname == cand_bname
                            and n_page == cand_page
                            and n_idx is not None
                            and abs(n_idx - cand_idx) == 1
                        ):
                            seen_chunk_ids.add(neighbor.chunk_id)
                            final_chunks.append(
                                DocumentChunk(
                                    chunk_id=neighbor.chunk_id,
                                    document_id=neighbor.document_id,
                                    text=neighbor.text,
                                    metadata=neighbor.metadata,
                                    score=round(cand.score * 0.95, 3),
                                )
                            )

        return final_chunks[:k]

    def get_all_documents(self) -> List[Dict[str, Any]]:
        total_count = self._collection.count()
        if total_count == 0:
            return []
        data = self._collection.get(include=["metadatas", "documents"])
        if not data or not data["ids"]:
            return []

        doc_map: Dict[str, Dict[str, Any]] = {}
        for i, meta in enumerate(data["metadatas"]):
            source = meta.get("source", "unknown") if meta else "unknown"
            if source not in doc_map:
                title = (
                    (meta.get("title") if meta else None)
                    or (meta.get("document_name") if meta else None)
                    or Path(source).name
                )
                doc_map[source] = {
                    "title": title,
                    "preview": data["documents"][i][:150]
                }

        items: List[Dict[str, Any]] = []
        for source, info in doc_map.items():
            items.append({
                "id": source,
                "title": info["title"],
                "content_preview": info["preview"],
            })
        return items
