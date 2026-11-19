import asyncio
import logging
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Request
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
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
from app.domain.interfaces import (
    VectorStoreProtocol,
    IngestionServiceProtocol,
    WorkflowServiceProtocol,
    FeedbackRepositoryProtocol,
)

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing application container...")
    app.state.container = Container()
    yield

app = FastAPI(title="RAG Technical Documentation Assistant", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_container(request: Request) -> Container:
    if hasattr(request.app.state, "container") and request.app.state.container is not None:
        return request.app.state.container
    return Container()

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.post("/query", response_model=QueryResponse)
async def execute_query(
    request: QueryRequest,
    container: Container = Depends(get_container)
) -> QueryResponse:
    logger.info("Processing query: %s (document_ids=%s)", request.question, request.document_ids)
    try:
        workflow_service: WorkflowServiceProtocol = container.get_workflow_service()
        result = await workflow_service.run(
            request.question,
            request.session_id,
            request.document_ids
        )
        return QueryResponse(
            answer=result.get("answer", "No answer could be generated."),
            sources=result.get("sources", []),
            retries=result.get("retries", 0),
            route=result.get("route", "generation"),
            relevance_score=result.get("relevance_score"),
            query_intent=result.get("query_intent"),
            rewritten_query=result.get("rewritten_query"),
        )
    except HTTPException:
        raise
    except Exception as e:
        err_msg = str(e).lower()
        if "rate limit" in err_msg or "429" in err_msg or "rate_limit" in err_msg:
            logger.warning("Provider rate limit encountered: %s", e)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Upstream AI provider rate limit reached. Please retry in a few moments."
            )
        elif "quota" in err_msg or "503" in err_msg or "overloaded" in err_msg:
            logger.warning("Provider service unavailable: %s", e)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Upstream AI model service is temporarily unavailable. Please retry in a few moments."
            )
        else:
            logger.exception("Unhandled error in execute_query")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Query execution failed: {e}"
            )

@app.post("/ingest", response_model=IngestResponse)
async def ingest_document(
    request: IngestRequest,
    container: Container = Depends(get_container)
) -> IngestResponse:
    target_path = Path(request.file_path).resolve()
    if not target_path.exists():
        raise HTTPException(status_code=404, detail="File does not exist")

    allowed_roots = [
        Path(settings.uploads_directory).resolve(),
        Path(settings.sample_directory).resolve(),
        (Path(__file__).resolve().parent.parent / "data" / "sample_docs").resolve(),
        (Path(__file__).resolve().parent.parent / "data" / "uploads").resolve(),
    ]

    is_allowed = any(target_path == root or root in target_path.parents for root in allowed_roots)
    if not is_allowed:
        logger.warning("Path traversal or unapproved path attempted in /ingest: %s", request.file_path)
        raise HTTPException(status_code=403, detail="File path must be within sample_docs or uploads directory")

    ingestion_service: IngestionServiceProtocol = container.get_ingestion_service()
    try:
        count = await asyncio.to_thread(ingestion_service.ingest_file, str(target_path))
        return IngestResponse(status="success", chunks_indexed=count)
    except ValueError as ve:
        raise HTTPException(status_code=422, detail=str(ve))
    except Exception as e:
        logger.exception("Error ingesting file %s", request.file_path)
        raise HTTPException(status_code=500, detail=f"Failed to ingest file: {e}")

@app.post("/upload", response_model=IngestResponse)
async def upload_document(
    file: UploadFile = File(...),
    container: Container = Depends(get_container)
) -> IngestResponse:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    safe_name = Path(file.filename).name
    if not safe_name or safe_name in [".", ".."]:
        raise HTTPException(status_code=400, detail="Invalid filename")

    suffix = Path(safe_name).suffix.lower()
    if suffix not in [".pdf", ".md", ".txt"]:
        raise HTTPException(status_code=400, detail=f"Unsupported file format '{suffix}'. Only .pdf, .md, and .txt files are allowed.")

    contents = await file.read()
    if len(contents) > 25 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File exceeds maximum size limit of 25 MB")

    if suffix == ".pdf":
        if not contents.startswith(b"%PDF-"):
            raise HTTPException(status_code=400, detail="Invalid PDF file format: missing %PDF- header")

    uploads_dir = Path(settings.uploads_directory)
    uploads_dir.mkdir(parents=True, exist_ok=True)
    destination = (uploads_dir / safe_name).resolve()

    # Prevent escaping uploads_dir
    if uploads_dir.resolve() not in destination.parents:
        raise HTTPException(status_code=400, detail="Invalid target file destination")

    destination.write_bytes(contents)

    ingestion_service: IngestionServiceProtocol = container.get_ingestion_service()
    try:
        chunks = await asyncio.to_thread(ingestion_service.ingest_file, str(destination))
        return IngestResponse(status="success", chunks_indexed=chunks)
    except ValueError as ve:
        logger.warning("Upload parsing failed for %s: %s", safe_name, ve)
        raise HTTPException(status_code=422, detail=str(ve))
    except Exception as e:
        logger.exception("Unexpected error processing upload %s", safe_name)
        raise HTTPException(status_code=500, detail=f"Failed to process file: {e}")

@app.post("/ingest/samples", response_model=IngestResponse)
async def ingest_samples(container: Container = Depends(get_container)) -> IngestResponse:
    ingestion_service: IngestionServiceProtocol = container.get_ingestion_service()
    sample_dir = Path(settings.sample_directory)
    if not sample_dir.exists():
        sample_dir = Path(__file__).resolve().parent.parent / "data" / "sample_docs"

    total_chunks = 0
    if sample_dir.exists():
        for file in sorted(sample_dir.iterdir()):
            if file.is_file() and file.suffix.lower() in [".md", ".txt", ".pdf"]:
                try:
                    count = await asyncio.to_thread(ingestion_service.ingest_file, str(file))
                    total_chunks += count
                except Exception as e:
                    logger.warning("Failed to ingest sample doc %s: %s", file.name, e)
    return IngestResponse(status="success", chunks_indexed=total_chunks)

@app.get("/documents", response_model=DocumentListResponse)
async def list_documents(container: Container = Depends(get_container)) -> DocumentListResponse:
    vector_store: VectorStoreProtocol = container.get_vector_store()
    docs = await asyncio.to_thread(vector_store.get_all_documents)
    return DocumentListResponse(documents=docs)

@app.delete("/documents/{document_id:path}")
async def delete_document_endpoint(
    document_id: str,
    container: Container = Depends(get_container)
):
    safe_name = Path(document_id).name
    uploads_dir = Path(settings.uploads_directory).resolve()
    target_file = (uploads_dir / safe_name).resolve()

    # If the physical file exists in uploads, remove it
    if target_file.exists() and uploads_dir in target_file.parents:
        try:
            target_file.unlink()
            logger.info("Deleted physical file: %s", target_file)
        except Exception as e:
            logger.warning("Failed to delete physical file %s: %s", target_file, e)

    # Remove from vector store and BM25 index
    vector_store = container.get_vector_store()
    await asyncio.to_thread(vector_store.delete_document, document_id)
    return {"status": "deleted", "document_id": document_id}

@app.post("/feedback", response_model=FeedbackResponse)
async def submit_feedback(
    request: FeedbackRequest,
    container: Container = Depends(get_container)
) -> FeedbackResponse:
    repo: FeedbackRepositoryProtocol = container.get_feedback_repository()
    feedback_id = repo.save_feedback(
        session_id=request.session_id,
        rating=request.rating,
        comment=request.comment,
        question=request.question,
        answer=request.answer,
    )
    return FeedbackResponse(status="recorded", feedback_id=feedback_id)
