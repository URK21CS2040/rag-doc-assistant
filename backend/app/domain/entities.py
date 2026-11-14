from pydantic import BaseModel, Field

class DocumentChunk(BaseModel):
    chunk_id: str
    document_id: str
    text: str
    metadata: dict = Field(default_factory=dict)
    score: float = 0.0

class GradedDocument(BaseModel):
    chunk: DocumentChunk
    is_relevant: bool
    score: float = 0.0
