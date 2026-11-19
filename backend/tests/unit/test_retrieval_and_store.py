from pathlib import Path
from typing import List
from app.domain.entities import DocumentChunk
from app.ingestion.vector_store import ChromaVectorStore

class MockEmbeddings:
    def __init__(self, model_name: str = "mock-model", dim: int = 4) -> None:
        self.model_name = model_name
        self.dim = dim

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        # Deterministic lightweight float vectors for testing
        return [[0.1 * (i + 1)] * self.dim for i in range(len(texts))]

    def embed_query(self, text: str) -> List[float]:
        return [0.1] * self.dim


def test_collection_metadata_and_versioning(tmp_path: Path):
    emb1 = MockEmbeddings(model_name="fastembed_bge", dim=384)
    store1 = ChromaVectorStore(embeddings=emb1, persist_directory=str(tmp_path / "chroma"))

    # Collection name should encode the model name
    assert "fastembed_bge" in store1._collection.name
    meta = store1._collection.metadata
    assert meta["dimension"] == 384
    assert meta["embedding_model"] == "fastembed_bge"
    assert meta["hnsw:space"] == "cosine"

    # Switching model creates a new isolated collection without clash
    emb2 = MockEmbeddings(model_name="openai_text_3_small", dim=1536)
    store2 = ChromaVectorStore(embeddings=emb2, persist_directory=str(tmp_path / "chroma"))
    assert "openai_text_3_small" in store2._collection.name
    assert store2._collection.metadata["dimension"] == 1536


def test_rrf_hybrid_search_and_document_filter(tmp_path: Path):
    emb = MockEmbeddings(model_name="mock_bge", dim=4)
    store = ChromaVectorStore(embeddings=emb, persist_directory=str(tmp_path / "chroma"))

    chunk_a = DocumentChunk(
        chunk_id="a1",
        document_id="DocA.pdf",
        text="EdgeWatch alert threshold is 0.85.",
        metadata={"source": "DocA.pdf", "page": 1},
        score=0.0
    )
    chunk_b = DocumentChunk(
        chunk_id="b1",
        document_id="DocB.pdf",
        text="Custom alert threshold is 0.42.",
        metadata={"source": "DocB.pdf", "page": 1},
        score=0.0
    )
    store.add_chunks([chunk_a, chunk_b])

    # Unfiltered search should find chunks
    all_results = store.similarity_search("alert threshold", k=5)
    assert len(all_results) >= 1

    # Scoped search to DocB.pdf should only return DocB
    scoped_results = store.similarity_search("alert threshold", k=5, document_ids=["DocB.pdf"])
    assert len(scoped_results) == 1
    assert scoped_results[0].document_id == "DocB.pdf"
    assert "0.42" in scoped_results[0].text

