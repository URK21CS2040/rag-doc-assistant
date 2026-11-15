import re
from typing import List, Dict, Any
import chromadb
from langchain_openai import OpenAIEmbeddings
from app.config import settings
from app.domain.entities import DocumentChunk

STOPWORDS = {
    'what', 'is', 'the', 'for', 'are', 'a', 'an', 'in', 'of', 'to', 'and', 'or', 'on',
    'with', 'by', 'at', 'from', 'this', 'that', 'it', 'does', 'how', 'why', 'can',
    'explain', 'show', 'tell', 'me', 'about', 'do', 'we', 'give', 'list', 'describe'
}

SYNONYMS = {
    'capacity': ['assets', 'maximum', 'supported', 'limit', 'devices', 'nodes'],
    'retention': ['buffer', 'hours', 'store', 'storage', 'retention_hours', 'retained'],
    'buffer': ['retention', 'offline', 'queue', 'hours', 'summaries'],
    'hardware': ['cpu', 'memory', 'ram', 'storage', 'ssd', 'requirements', 'minimum'],
    'requirements': ['requirement', 'specifications', 'minimum', 'recommended', 'config'],
    'latency': ['delay', 'timing', 'response', 'seconds', 'event'],
    'oops': ['object-oriented', 'oop', 'class', 'classes', 'inheritance', 'polymorphism', 'encapsulation', 'abstraction'],
    'oop': ['object-oriented', 'oops', 'class', 'classes', 'inheritance', 'polymorphism', 'encapsulation', 'abstraction'],
    'ml': ['machine learning', 'machine', 'learning', 'supervised', 'unsupervised', 'reinforcement', 'semi-supervised', 'classification', 'regression'],
    'machine': ['machine learning', 'ml'],
    'learning': ['supervised', 'unsupervised', 'machine learning', 'reinforcement', 'semi-supervised'],
    'types': ['type', 'kinds', 'categories', 'classification', 'pillars'],
    'supervised': ['supervised learning', 'labelled', 'classification', 'regression'],
    'unsupervised': ['unsupervised learning', 'clustering', 'k-means', 'pca', 'association'],
    'reinforcement': ['reinforcement learning', 'agent', 'reward', 'actions', 'policy'],
    'unavailable': ['outage', 'disconnect', 'offline', 'central', 'connectivity', 'failure', 'sync'],
    'central': ['service', 'sync', 'unavailable', 'centralized', 'cloud'],
    'critical': ['threshold', 'alert', '0.85', 'warning', 'severity'],
    'threshold': ['critical', 'warning', '0.85', '0.60', 'cutoff', 'alert'],
    'overlap': ['window', 'rolling', 'inference', 'stride', '50%', 'seconds'],
}

def get_stem(w: str) -> str:
    for suff in ['ation', 'tion', 'ments', 'ment', 'ing', 'ed', 'ies', 'es', 's']:
        if w.endswith(suff) and len(w) - len(suff) >= 3:
            return w[:-len(suff)]
    return w

class ChromaVectorStore:
    def __init__(self, embeddings: OpenAIEmbeddings) -> None:
        self._embeddings = embeddings
        self._client = chromadb.PersistentClient(path=settings.chroma_persist_directory)
        self._collection = self._client.get_or_create_collection(name="technical_docs")

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

    def delete_document(self, document_id: str) -> None:
        try:
            self._collection.delete(where={"source": document_id})
        except Exception as e:
            print(f"Error deleting document {document_id}: {e}")

    def similarity_search(self, query: str, k: int = 4) -> List[DocumentChunk]:
        total_count = self._collection.count()
        if total_count == 0:
            return []

        query_embedding = self._embeddings.embed_query(query)
        pool_size = min(max(k * 3, 10), min(25, total_count))
        results = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=pool_size
        )
        if not results or not results["ids"] or not results["ids"][0]:
            return []

        ids = results["ids"][0]
        documents = results["documents"][0]
        metadatas = results["metadatas"][0]
        distances = results.get("distances", [[]])[0] if results.get("distances") else []

        q_clean = query.lower()
        q_tokens = [w for w in re.findall(r'[a-zA-Z0-9_\-\.%]+', q_clean) if len(w) > 1 and w not in STOPWORDS]

        scored_candidates = []
        for i in range(len(ids)):
            dist = distances[i] if i < len(distances) else 1.0
            # Convert vector distance to cosine similarity
            cos_sim = max(0.0, min(1.0, 1.0 - (dist / 2.0)))
            doc_text = documents[i]
            meta = metadatas[i] if i < len(metadatas) else {}
            src = meta.get("source", "unknown")
            doc_lower = doc_text.lower()
            src_lower = src.lower()

            if not q_tokens:
                hybrid_score = cos_sim
            else:
                matched_count = 0
                synonym_matched = 0
                for tok in q_tokens:
                    tok_stem = get_stem(tok)
                    if tok in doc_lower or (len(tok_stem) >= 3 and tok_stem in doc_lower):
                        matched_count += 1
                    elif tok in SYNONYMS:
                        if any(syn in doc_lower for syn in SYNONYMS[tok]):
                            synonym_matched += 1

                token_ratio = (matched_count + 0.8 * synonym_matched) / len(q_tokens)

                # Check multi-token phrase match
                phrase_match = False
                exact_standalone_phrase = False
                for p_idx in range(len(q_tokens) - 1):
                    phrase = f"{q_tokens[p_idx]} {q_tokens[p_idx + 1]}"
                    if phrase in doc_lower:
                        phrase_match = True
                        if re.search(r'(?<![a-zA-Z\-])' + re.escape(phrase) + r'(?![a-zA-Z\-])', doc_lower):
                            exact_standalone_phrase = True
                        break

                # Check if chunk contains a direct section header or numbered item matching the query
                header_match = False
                for tok in q_tokens:
                    if len(tok) >= 4 and re.search(r'(?m)^[0-9#\.\s*_-]+' + re.escape(tok), doc_lower):
                        header_match = True
                        break

                source_match = any(tok in src_lower for tok in q_tokens if len(tok) > 3)
                entity_match = any(tok in doc_lower for tok in q_tokens if len(tok) >= 5 and tok not in STOPWORDS)
                is_fragment_start = bool(re.match(r'^\s*[a-z]', doc_text))

                if token_ratio == 0 and not phrase_match and not source_match:
                    hybrid_score = cos_sim * 0.35
                else:
                    lex_score = token_ratio * 0.65
                    if exact_standalone_phrase:
                        lex_score += 0.30
                    elif phrase_match:
                        lex_score += 0.15

                    if header_match:
                        lex_score += 0.20
                    if source_match:
                        lex_score += 0.15
                    elif entity_match:
                        lex_score += 0.05

                    if is_fragment_start:
                        lex_score -= 0.35

                    hybrid_score = 0.25 * cos_sim + 0.75 * min(1.0, max(0.0, lex_score))

            final_score = round(min(0.98, max(0.0, hybrid_score)), 3)
            scored_candidates.append(
                (
                    final_score,
                    DocumentChunk(
                        chunk_id=ids[i],
                        document_id=src,
                        text=doc_text,
                        metadata=meta,
                        score=final_score
                    )
                )
            )

        scored_candidates.sort(key=lambda x: x[0], reverse=True)
        return [chunk for _, chunk in scored_candidates[:k]]

    def get_all_documents(self) -> List[Dict[str, Any]]:
        data = self._collection.get()
        if not data or not data["ids"]:
            return []

        doc_map: Dict[str, str] = {}
        for i, meta in enumerate(data["metadatas"]):
            source = meta.get("source", "unknown")
            if source not in doc_map:
                doc_map[source] = data["documents"][i][:150]

        items: List[Dict[str, Any]] = []
        for source, preview in doc_map.items():
            items.append({
                "id": source,
                "title": source,
                "content_preview": preview
            })
        return items
