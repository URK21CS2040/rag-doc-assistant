from typing import List, Dict, Any
import chromadb
from langchain_openai import OpenAIEmbeddings
from app.config import settings
from app.domain.entities import DocumentChunk

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

    def similarity_search(self, query: str, k: int = 4) -> List[DocumentChunk]:
        query_embedding = self._embeddings.embed_query(query)
        results = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=k
        )
        chunks: List[DocumentChunk] = []
        if not results or not results["ids"] or not results["ids"][0]:
            return chunks
        
        ids = results["ids"][0]
        documents = results["documents"][0]
        metadatas = results["metadatas"][0]
        distances = results.get("distances", [[]])[0] if results.get("distances") else []

        for i in range(len(ids)):
            dist = distances[i] if i < len(distances) else 1.0
            # Convert distance between unit-normalized vectors to cosine similarity score [0.0, 1.0]
            sim = max(0.0, min(1.0, 1.0 - (dist / 2.0)))
            chunks.append(
                DocumentChunk(
                    chunk_id=ids[i],
                    document_id=metadatas[i].get("source", "unknown"),
                    text=documents[i],
                    metadata=metadatas[i],
                    score=round(sim, 3)
                )
            )
        return chunks

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
