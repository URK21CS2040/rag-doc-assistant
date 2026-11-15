import shutil
from pathlib import Path
from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from app.schemas import (
    QueryRequest,
    QueryResponse,
    IngestRequest,
    IngestResponse,
    DocumentListResponse,
    FeedbackRequest,
    FeedbackResponse,
)
from app.core.container import Container
from app.domain.interfaces import VectorStoreProtocol, IngestionServiceProtocol, WorkflowServiceProtocol, FeedbackRepositoryProtocol

app = FastAPI(title="RAG Technical Documentation Assistant", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_container() -> Container:
    return Container()

@app.post("/query", response_model=QueryResponse)
async def execute_query(request: QueryRequest, container: Container = Depends(get_container)) -> QueryResponse:
    print(f"[QUERY] User question: {request.question}")
    try:
        workflow_service: WorkflowServiceProtocol = container.get_workflow_service()
        result = await workflow_service.run(request.question, request.session_id)
        return QueryResponse(
            answer=result.get("answer", "No answer could be generated."),
            sources=result.get("sources", []),
            retries=result.get("retries", 0),
            relevance_score=result.get("relevance_score"),
            query_intent=result.get("query_intent"),
            rewritten_query=result.get("rewritten_query")
        )
    except Exception as e:
        print(f"Unhandled error in execute_query: {e}")
        return QueryResponse(
            answer="The AI model service is currently experiencing high load or a rate limit window. Please retry your question in a few moments.",
            sources=[],
            retries=0,
            relevance_score=0.0,
            query_intent="Notice",
            rewritten_query=request.question
        )

@app.post("/ingest", response_model=IngestResponse)
async def ingest_document(request: IngestRequest, container: Container = Depends(get_container)) -> IngestResponse:
    ingestion_service: IngestionServiceProtocol = container.get_ingestion_service()
    count = ingestion_service.ingest_file(request.file_path)
    return IngestResponse(status="success", chunks_indexed=count)

@app.post("/upload", response_model=IngestResponse)
async def upload_document(
    file: UploadFile = File(...),
    container: Container = Depends(get_container)
) -> IngestResponse:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    
    sample_dir = Path(__file__).resolve().parent.parent / "data" / "sample_docs"
    sample_dir.mkdir(parents=True, exist_ok=True)
    destination = sample_dir / file.filename
    
    with open(destination, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    ingestion_service: IngestionServiceProtocol = container.get_ingestion_service()
    chunks = ingestion_service.ingest_file(str(destination))
    return IngestResponse(status="success", chunks_indexed=chunks)

@app.post("/ingest/samples", response_model=IngestResponse)
async def ingest_samples(container: Container = Depends(get_container)) -> IngestResponse:
    ingestion_service: IngestionServiceProtocol = container.get_ingestion_service()
    sample_dir = Path(__file__).resolve().parent.parent / "data" / "sample_docs"
    total_chunks = 0
    if sample_dir.exists():
        for file in sorted(sample_dir.iterdir()):
            if file.is_file() and file.suffix.lower() in [".md", ".txt", ".pdf"]:
                total_chunks += ingestion_service.ingest_file(str(file))
    return IngestResponse(status="success", chunks_indexed=total_chunks)

@app.get("/documents", response_model=DocumentListResponse)
async def list_documents(container: Container = Depends(get_container)) -> DocumentListResponse:
    vector_store: VectorStoreProtocol = container.get_vector_store()
    docs = vector_store.get_all_documents()
    return DocumentListResponse(documents=docs)

@app.post("/feedback", response_model=FeedbackResponse)
async def submit_feedback(request: FeedbackRequest, container: Container = Depends(get_container)) -> FeedbackResponse:
    repo: FeedbackRepositoryProtocol = container.get_feedback_repository()
    feedback_id = repo.save_feedback(request.session_id, request.rating, request.comment)
    return FeedbackResponse(status="recorded", feedback_id=feedback_id)
