# RAG-Based Technical Documentation Assistant

A production-ready, Dockerized monorepo implementing a self-corrective Retrieval-Augmented Generation (RAG) system using Python 3.11 (FastAPI, LangGraph, Pydantic v2, ChromaDB, Groq LPU LLM) and React 18 + TypeScript (Vite, Tailwind CSS, Lucide React).

## Architecture Overview
- **Default LLM Engine**: Groq API (`llama-3.3-70b-versatile` / `openai/gpt-oss-120b` via ultra-fast LPU inference at `https://api.groq.com/openai/v1`). Also supports Grok (xAI) and OpenAI.
- **Ingestion Pipeline**: Loads technical Markdown and PDF documentation, splits them via recursive character token splitting, generates dense embeddings, and stores them in ChromaDB.
- **LangGraph Workflow**: Implements Query Analysis, Vector Retrieval, LLM Document Grading (self-correction with retry loops), and Answer Generation with grounded citations.
- **FastAPI Backend**: Adheres to strict SOLID principles using typing protocols, dependency injection, and Pydantic v2 validation.
- **React Frontend**: Modern responsive dashboard with real-time Q&A, source citation inspection, document inventory management, and feedback submission.

## How It Works

```text
Document
   ↓
Text Extraction
   ↓
Text Chunking
   ↓
Embedding Generation
   ↓
Vector Search (ChromaDB)
   ↓
Relevant Context (Grading / Fallback)
   ↓
LLM (Groq LPU)
   ↓
Answer (with Citations & Explainability)
```

### Pipeline Breakdown:
1. **Document**: Source technical documentation in Markdown (`.md`) or PDF (`.pdf`) format.
2. **Text Extraction**: Ingestion loaders extract raw text (using `pypdf` for PDF parsing and UTF-8 decoders for Markdown).
3. **Text Chunking**: Recursive character chunking splits the document into coherent, overlapping chunks to retain semantic context.
4. **Embedding Generation**: Text chunks are converted into dense vector representations.
5. **Vector Search**: User queries trigger semantic similarity searches in ChromaDB to retrieve the most relevant passages.
6. **Relevant Context & Grading**: A self-corrective evaluator grades the retrieved chunks (`>= 0.70`). If relevant, they are forwarded; if not, query rewriting or live web search (Tavily) activates.
7. **LLM**: Groq Cloud's LPU inference engine processes the prompt, user intent, and contextual evidence.
8. **Answer**: The system delivers a grounded, structured answer with interactive citations and a complete pipeline trace.

## Project Structure

```text
rag-doc-assistant/
├── backend/
│   ├── app/
│   │   ├── core/              # Dependency injection container & LLM Factory
│   │   │   ├── container.py
│   │   │   └── llm_factory.py # GroqCloud, Grok xAI, and OpenAI clients
│   │   ├── domain/            # Domain entities and typing interfaces
│   │   ├── ingestion/         # Loaders (PDF & Markdown), chunker, vector store
│   │   │   ├── chunker.py
│   │   │   ├── loaders.py     # Document text extractors
│   │   │   └── vector_store.py# ChromaDB integration
│   │   ├── storage/           # Repositories for user feedback
│   │   ├── workflow/          # LangGraph state machine & prompts
│   │   │   ├── graph.py       # Graph definition & edge conditions
│   │   │   ├── nodes.py       # Query analysis, retrieval, grading, generation
│   │   │   ├── prompts.py     # Intent & generation prompt templates
│   │   │   └── state.py       # TypedDict graph state
│   │   ├── config.py          # Pydantic v2 application settings
│   │   ├── main.py            # FastAPI endpoints & routes
│   │   └── schemas.py         # Request/response validation schemas
│   ├── data/
│   │   ├── chroma/            # Persistent vector database
│   │   └── sample_docs/       # Bundled sample technical documentation
│   ├── tests/                 # Unit and integration test suite
│   ├── Dockerfile             # Multi-stage Python 3.11 container
│   ├── requirements.txt       # Backend dependencies
│   └── pytest.ini             # Test runner configuration
├── frontend/
│   ├── src/
│   │   ├── api/               # API client (submitQuery, fetchDocuments, feedback)
│   │   ├── components/        # MarkdownView custom renderer
│   │   ├── types/             # TypeScript API interfaces
│   │   ├── App.tsx            # Main chat interface & Explainability Drawer
│   │   └── main.tsx           # React entry point
│   ├── nginx.conf             # Production Nginx reverse proxy
│   ├── Dockerfile             # Multi-stage Node.js build + Nginx Alpine
│   └── package.json           # Frontend dependencies
├── docker-compose.yml         # Container orchestration
├── .env.example               # Sanitized environment template
└── README.md                  # Project documentation
```

## Setup & Running with Docker
1. Set your Groq API key in `.env`:
   ```bash
   cp .env.example .env
   # Add your GROQ_API_KEY=gsk_...
   ```
2. Build and run containers:
   ```bash
   docker-compose up --build -d
   ```
3. Access the Web UI at `http://localhost` and API Docs at `http://localhost:8000/docs`.
