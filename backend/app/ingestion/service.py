from app.ingestion.loaders import MarkdownLoader
from app.ingestion.chunker import TextChunker
from app.ingestion.vector_store import ChromaVectorStore

class IngestionService:
    def __init__(self, vector_store: ChromaVectorStore) -> None:
        self._vector_store = vector_store
        self._loader = MarkdownLoader()
        self._chunker = TextChunker()

    def ingest_file(self, file_path: str) -> int:
        content = self._loader.load(file_path)
        if not content:
            return 0
        chunks = self._chunker.split_text(file_path, content)
        self._vector_store.add_chunks(chunks)
        return len(chunks)
