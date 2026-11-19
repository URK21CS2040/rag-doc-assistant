from typing import Any
from app.core.llm_factory import LLMFactory
from app.ingestion.vector_store import ChromaVectorStore
from app.ingestion.service import IngestionService
from app.storage.repositories import SQLiteFeedbackRepository
from app.workflow.graph import WorkflowService

class Container:
    def __init__(self, vector_store: Any = None, embeddings: Any = None, chat_model: Any = None) -> None:
        self._embeddings = embeddings or LLMFactory.create_embeddings()
        self._chat_model = chat_model or LLMFactory.create_chat_model()
        self._vector_store = vector_store or ChromaVectorStore(embeddings=self._embeddings)
        self._ingestion_service = IngestionService(vector_store=self._vector_store)
        self._feedback_repository = SQLiteFeedbackRepository()
        self._workflow_service = WorkflowService(vector_store=self._vector_store, chat_model=self._chat_model)

    def get_vector_store(self) -> ChromaVectorStore:
        return self._vector_store

    def get_ingestion_service(self) -> IngestionService:
        return self._ingestion_service

    def get_feedback_repository(self) -> SQLiteFeedbackRepository:
        return self._feedback_repository

    def get_workflow_service(self) -> WorkflowService:
        return self._workflow_service
