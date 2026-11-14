from app.core.llm_factory import LLMFactory
from app.ingestion.vector_store import ChromaVectorStore
from app.ingestion.service import IngestionService
from app.storage.repositories import InMemoryFeedbackRepository
from app.workflow.graph import WorkflowService

class Container:
    def __init__(self) -> None:
        self._embeddings = LLMFactory.create_embeddings()
        self._chat_model = LLMFactory.create_chat_model()
        self._vector_store = ChromaVectorStore(embeddings=self._embeddings)
        self._ingestion_service = IngestionService(vector_store=self._vector_store)
        self._feedback_repository = InMemoryFeedbackRepository()
        self._workflow_service = WorkflowService(vector_store=self._vector_store, chat_model=self._chat_model)

    def get_vector_store(self) -> ChromaVectorStore:
        return self._vector_store

    def get_ingestion_service(self) -> IngestionService:
        return self._ingestion_service

    def get_feedback_repository(self) -> InMemoryFeedbackRepository:
        return self._feedback_repository

    def get_workflow_service(self) -> WorkflowService:
        return self._workflow_service
