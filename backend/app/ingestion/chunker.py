from typing import List
from app.domain.entities import DocumentChunk

class TextChunker:
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50) -> None:
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap

    def split_text(self, document_id: str, text: str) -> List[DocumentChunk]:
        chunks: List[DocumentChunk] = []
        start = 0
        text_length = len(text)
        index = 0
        while start < text_length:
            end = min(start + self._chunk_size, text_length)
            chunk_content = text[start:end]
            chunk_id = f"{document_id}_chunk_{index}"
            chunks.append(
                DocumentChunk(
                    chunk_id=chunk_id,
                    document_id=document_id,
                    text=chunk_content,
                    metadata={"source": document_id}
                )
            )
            start += self._chunk_size - self._chunk_overlap
            index += 1
        return chunks
