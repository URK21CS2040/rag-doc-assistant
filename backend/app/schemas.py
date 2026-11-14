from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1)
    session_id: Optional[str] = Field(default=None)

class SourceCitation(BaseModel):
    document_id: str
    chunk_text: str
    score: float

class QueryResponse(BaseModel):
    answer: str
    sources: List[SourceCitation]
    retries: int
    relevance_score: Optional[float] = None
    query_intent: Optional[str] = None
    rewritten_query: Optional[str] = None

class IngestRequest(BaseModel):
    file_path: str

class IngestResponse(BaseModel):
    status: str
    chunks_indexed: int

class DocumentItem(BaseModel):
    id: str
    title: str
    content_preview: str

class DocumentListResponse(BaseModel):
    documents: List[DocumentItem]

class FeedbackRequest(BaseModel):
    session_id: str
    rating: str = Field(..., pattern="^(thumbs_up|thumbs_down)$")
    comment: Optional[str] = Field(default=None)

class FeedbackResponse(BaseModel):
    status: str
    feedback_id: str
