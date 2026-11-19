import logging
from app.ingestion.loaders import MarkdownLoader
from app.ingestion.chunker import TextChunker
from app.ingestion.vector_store import ChromaVectorStore

logger = logging.getLogger(__name__)

class IngestionService:
    def __init__(self, vector_store: ChromaVectorStore) -> None:
        self._vector_store = vector_store
        self._loader = MarkdownLoader()
        self._chunker = TextChunker()

    def ingest_file(self, file_path: str) -> int:
        content = self._loader.load(file_path)
        if not content or not content.strip():
            raise ValueError("No extractable text found in file")
        chunks = self._chunker.split_text(file_path, content)
        if not chunks:
            raise ValueError("No indexable chunks could be generated from file")
        self._vector_store.delete_document(file_path)
        self._vector_store.add_chunks(chunks)
        logger.info("Successfully ingested %d chunks from %s", len(chunks), file_path)
        return len(chunks)
