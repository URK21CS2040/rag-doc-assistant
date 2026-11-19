from typing import Protocol, List, Dict, Any, Optional
from app.domain.entities import DocumentChunk

class VectorStoreProtocol(Protocol):
    def add_chunks(self, chunks: List[DocumentChunk]) -> None:
        ...
    def similarity_search(self, query: str, k: int = 5, document_ids: Optional[List[str]] = None) -> List[DocumentChunk]:
        ...
    def get_all_documents(self) -> List[Dict[str, Any]]:
        ...

class IngestionServiceProtocol(Protocol):
    def ingest_file(self, file_path: str) -> int:
        ...

class WorkflowServiceProtocol(Protocol):
    async def run(
        self,
        question: str,
        session_id: Optional[str] = None,
        document_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        ...

class FeedbackRepositoryProtocol(Protocol):
    def save_feedback(
        self,
        session_id: str,
        rating: str,
        comment: Optional[str] = None,
        question: Optional[str] = None,
        answer: Optional[str] = None,
    ) -> str:
        ...
