from typing import List, Dict, Any, TypedDict, Optional
from app.domain.entities import DocumentChunk

class GraphState(TypedDict, total=False):
    question: str
    rewritten_query: str
    query_intent: str
    retrieved_chunks: List[DocumentChunk]
    filtered_chunks: List[DocumentChunk]
    retries: int
    route: str
    document_ids: Optional[List[str]]
    answer: str
    sources: List[Dict[str, Any]]
    relevance_score: float
    session_id: Optional[str]
    chat_history: Optional[List[Dict[str, str]]]
