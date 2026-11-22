import re
import logging
from pathlib import Path
from typing import Dict, Any
from app.config import settings
from app.ingestion.loaders import MarkdownLoader, UrlLoader
from app.ingestion.chunker import TextChunker
from app.ingestion.vector_store import ChromaVectorStore

logger = logging.getLogger(__name__)

class IngestionService:
    def __init__(self, vector_store: ChromaVectorStore) -> None:
        self._vector_store = vector_store
        self._loader = MarkdownLoader()
        self._url_loader = UrlLoader()
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

    def ingest_url(self, url: str) -> Dict[str, Any]:
        url = url.strip()
        title, content = self._url_loader.load(url)
        if not content or not content.strip():
            raise ValueError("No extractable text found at URL")

        # Save an archived markdown copy in uploads directory
        try:
            uploads_dir = Path(settings.uploads_directory)
            uploads_dir.mkdir(parents=True, exist_ok=True)
            safe_slug = re.sub(r'[^a-zA-Z0-9_-]', '_', url.replace("https://", "").replace("http://", ""))[:80]
            archive_path = uploads_dir / f"web_{safe_slug}.md"
            archive_header = f"# {title}\n\n**Source URL:** {url}\n\n---\n\n"
            archive_path.write_text(archive_header + content, encoding="utf-8")
        except Exception as e:
            logger.warning("Could not archive scraped URL to disk: %s", e)

        # Chunk the content using document_id = url
        chunks = self._chunker.split_text(url, content)
        if not chunks:
            raise ValueError("No indexable chunks could be generated from URL content")

        for c in chunks:
            c.metadata["title"] = title
            c.metadata["document_name"] = title
            c.metadata["source"] = url
            c.metadata["url"] = url

        self._vector_store.delete_document(url)
        self._vector_store.add_chunks(chunks)
        logger.info("Successfully ingested %d chunks from URL '%s' (title: '%s')", len(chunks), url, title)
        return {
            "status": "success",
            "chunks_indexed": len(chunks),
            "url": url,
            "title": title,
        }
