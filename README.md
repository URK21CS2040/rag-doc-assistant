# RAG-Based Technical Documentation Assistant

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-StateGraph-FF6F00?logo=langchain&logoColor=white)](https://langchain-ai.github.io/langgraph/)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector_Store-FF4F00)](https://www.trychroma.com/)
[![Groq LPU](https://img.shields.io/badge/Groq-LPU_Inference-F55036)](https://groq.com/)
[![React](https://img.shields.io/badge/React-18_TypeScript-61DAFB?logo=react&logoColor=black)](https://react.dev/)
[![Docker](https://img.shields.io/badge/Docker-Compose_Ready-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)

A production-grade, self-corrective Retrieval-Augmented Generation (RAG) assistant for complex technical documentation and live web research. Built on a **FastAPI + LangGraph** reactive workflow, **ChromaDB** dense-lexical vector store with FastEmbed semantic embeddings (`BAAI/bge-small-en-v1.5`), **GroqCloud LPU** high-throughput inference with resilient multi-tier fallback chains, **Tavily Advanced** web search, and a modern **React 18 + TypeScript** dashboard.

---

## Key Features

- **Document-First Grounding:** Strict prioritization of local technical PDF, Markdown, and scraped web documentation over external sources. External web search is only used when local context is genuinely insufficient.
- **Multi-Format Ingestion:**
  - **Local Files:** Upload `.pdf` and `.md` technical manuals, specifications, and architecture documents.
  - **Public Web URLs:** Scrape and index public web documentation (`POST /ingest-url`) with built-in SSRF protection against private IP ranges and localhost probing.
  - **Document Management:** Delete individual documents (`DELETE /documents/{id}`) or perform a bulk wipe (`DELETE /documents?confirm=true`) with automated ChromaDB vector cleanup.
- **Hybrid Retrieval & Dense Safety Net:**
  - FastEmbed dense vector embeddings (`BAAI/bge-small-en-v1.5`, 384-dim) combined with exact phrase matching, domain keyword boosting, and document auto-scoping.
  - **Dense Retrieval Safety Net:** When dense similarity is high ($\ge 0.80$), relevant chunks are protected against LLM grader stylistic mismatches (e.g. terse facts vs. long narrative scenario questions).
- **Resilient Multi-Tier LLM Generation:**
  - Multi-model fallback chain: `openai/gpt-oss-20b` $\rightarrow$ `qwen/qwen3.8-27b` $\rightarrow$ `openai/gpt-oss-120b`.
  - Expanded 3,000 output-token budgets to eliminate truncation (`finish_reason="length"`).
  - Explicit empty-generation detection: triggers fallback even if the primary model returns HTTP 200 with 0 content tokens.
  - Internal reasoning isolation: reasoning tokens from reasoning models are captured in telemetry logs and strictly excluded from user-facing answers.
  - Smart rate-limit (HTTP 429) & timeout handling: instantly transitions to alternative model pools rather than repeatedly hammering throttled models.
- **Tavily Advanced Web Search Fallback:**
  - Uses `search_depth="advanced"` for deep, comprehensive web extraction.
  - **Zero Confirmation Bias:** Removes synthetic search summaries from the context to prevent hallucinated consensus.
  - **Statistical Recency & Conflict Resolution:** Distinguishes between historical intermediate milestones (e.g., reaching 200 sixes in 2019) and current career totals (e.g., 264 sixes), while accounting for non-monotonic metrics, measurement windows, and source authority.
  - **Discrepancy Disclosure:** Explicitly notes differences when reputable sources disagree rather than inventing false certainty.
  - **Citation-Aligned Explainability:** Parses inline `[n]` citations and highlights only the specific sources supporting the final answer.
- **Self-Corrective LangGraph Architecture:** State machine supporting query intent classification, pronoun coreference resolution across multi-turn chats, query rewrites on retry, and verified source grounding.
- **Full Dockerization:** Multi-stage backend (`uvicorn`) and frontend (`nginx`) containers orchestrated via `docker-compose`.

---

## System Architecture

```text
                                  ┌──────────────────────────┐
                                  │   User Query (Client)    │
                                  └────────────┬─────────────┘
                                               │
                                               ▼
                                  ┌──────────────────────────┐
                                  │   Query Analysis Node    │
                                  │  - Intent Classification │
                                  │  - Pronoun Coreference   │
                                  │  - Target Document Scope │
                                  └────────────┬─────────────┘
                                               │
                                               ▼
                                  ┌──────────────────────────┐
                                  │     Retrieval Node       │
                                  │  - FastEmbed Dense Search│
                                  │  - ChromaDB Top-K Search │
                                  └────────────┬─────────────┘
                                               │
                                               ▼
                                  ┌──────────────────────────┐
                                  │  Document Grading Node   │
                                  │  - Dense Safety Net (≥.8)│
                                  │  - LLM Batch Relevance   │
                                  │  - Keyword Protection    │
                                  └───────┬──────────┬───────┘
                     Relevant Chunks      │          │  Insufficient Local
                    (Document Match)      │          │  Information
                                          ▼          ▼
                           ┌──────────────────┐  ┌──────────────────┐
                           │ Generation Node  │  │  Fallback Node   │
                           │ - Multi-Tier LLM │  │  - Tavily Adv.   │
                           │   Fallback Chain │  │  - Date/Milestone│
                           │ - Token Budgets  │  │    Resolution    │
                           │ - Citations [n]  │  │  - Discrepancies │
                           └──────────┬───────┘  └────────┬─────────┘
                                      │                   │
                                      ▼                   ▼
                           ┌────────────────────────────────────────┐
                           │  Interactive Answer + Page Citations   │
                           │     + Pipeline Route & Explainability  │
                           └────────────────────────────────────────┘
```

---

## Project Structure

```text
rag-doc-assistant/
├── backend/
│   ├── app/
│   │   ├── core/              # Dependency injection & multi-model LLM factory
│   │   │   ├── container.py
│   │   │   └── llm_factory.py # Groq LPU multi-model fallback chain, FastEmbed embeddings
│   │   ├── domain/            # Domain entities and typing interfaces
│   │   │   ├── entities.py    # DocumentChunk, IngestedDocument, Feedback
│   │   │   └── interfaces.py  # Strict SOLID protocols
│   │   ├── ingestion/         # Document parsers, chunking, and ChromaDB
│   │   │   ├── chunker.py     # Recursive character token splitting
│   │   │   ├── loaders.py     # PDF (pypdf), Markdown, and Web URL extractors with SSRF defense
│   │   │   ├── service.py     # Ingestion coordination & document deletion
│   │   │   └── vector_store.py# ChromaDB persistent vector store & hybrid search
│   │   ├── storage/           # Persistent feedback & metadata repositories
│   │   ├── workflow/          # LangGraph state machine
│   │   │   ├── graph.py       # Graph definition & conditional edge routing
│   │   │   ├── nodes.py       # Analysis, retrieval, grading, generation, fallback
│   │   │   ├── prompts.py     # Grounded, date-aware, anti-hallucination prompts
│   │   │   └── state.py       # TypedDict graph state definitions
│   │   ├── config.py          # Pydantic v2 application configuration
│   │   ├── main.py            # FastAPI REST API endpoints
│   │   └── schemas.py         # Request and response models
│   ├── data/
│   │   ├── chroma/            # Persistent ChromaDB storage
│   │   └── sample_docs/       # Technical specifications & concept manuals
│   ├── tests/                 # Integration and unit test suite (28 passing tests)
│   ├── Dockerfile             # Multi-stage Python 3.11 container
│   └── requirements.txt       # Backend dependencies
├── frontend/
│   ├── src/
│   │   ├── api/               # Typed HTTP client (query, documents, URL ingest, feedback)
│   │   ├── components/        # MarkdownView custom renderer, drawer, upload & URL modals
│   │   ├── types/             # TypeScript API interfaces
│   │   ├── App.tsx            # Main chat application & pipeline trace view
│   │   └── main.tsx           # React entry point
│   ├── nginx.conf             # Production Nginx reverse proxy
│   ├── Dockerfile             # Multi-stage Node.js build + Nginx Alpine
│   └── package.json           # Frontend dependencies
├── docker-compose.yml         # Container orchestration
├── .env.example               # Template environment configuration
└── README.md                  # Project documentation
```

---

## API Reference

The backend exposes an interactive OpenAPI specification at `http://localhost:8000/docs`.

| Method | Endpoint | Description | Payload / Response |
| :--- | :--- | :--- | :--- |
| `POST` | `/query` | Execute question through RAG LangGraph workflow | `{ "question": "...", "document_ids": [...] }` $\rightarrow$ Answer, Sources, Route, Relevance Score |
| `POST` | `/upload` | Multipart upload and index new `.pdf` or `.md` files | `multipart/form-data` $\rightarrow$ Status confirmation & chunk count |
| `POST` | `/ingest-url` | Scrape, parse, and index a public web documentation URL | `{ "url": "https://..." }` $\rightarrow$ Status, title, chunks indexed |
| `GET` | `/documents` | List all indexed documents with snippet previews | Array of document metadata and content previews |
| `DELETE` | `/documents/{id}` | Remove a single document and its vectors from ChromaDB | Status confirmation |
| `DELETE` | `/documents` | Bulk delete all indexed documents (`?confirm=true`) | Status confirmation & deleted count |
| `POST` | `/feedback` | Submit user thumbs-up/down feedback | `{ "session_id": "...", "rating": "thumbs_up", "comment": "..." }` |

---

## Verification & Test Results

The application has been verified across technical documentation, statistical recency, conflict resolution, and negative test cases:

| # | Question / Scenario | Expected Behavior | Observed Result | Route | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | **AS-TS-204 Critical Threshold** | Retrieve exact threshold from technical document | Answered verbatim from document with page citation | `generation` | **Verified** |
| 2 | **EdgeWatch System Specs** | Multi-specification lookup for gateway capacity & buffer | Extracted complete specifications under structured points | `generation` | **Verified** |
| 3 | **React Component vs Element** | Scoped conceptual comparison from React docs | Grounded definitions citing source chunks | `generation` | **Verified** |
| 4 | **Career Totals vs Milestones** (*"How many sixes did MS Dhoni hit in his entire IPL career?"*) | Prioritize updated career total (264) over older 2019 milestone (203) | Answered **264 sixes**, cited ESPN, excluded outdated milestone | `web_search` | **Verified** |
| 5 | **Outdated Milestone Handling** (*"How many centuries has Virat Kohli scored in the IPL?"*) | Identify current career record (9) over older historical counts | Reported 9 centuries with authoritative sources | `web_search` | **Verified** |
| 6 | **Dynamic Measurements** (*"Distance of Voyager 1 from Earth today"*) | Disclose continuously changing distance by measurement date | Outlined date-specific measurements & explained dynamics | `web_search` | **Verified** |
| 7 | **Uncovered / Nonsense Entity** | Explicitly state lack of reliable information | Declined to invent numbers; reported unverified | `web_search` | **Verified** |
| 8 | **Public URL Web Ingestion** | Ingest external URL, chunk, embed, and query | Clean text extraction and instant question answering | `generation` | **Verified** |

### Automated Test Suite Execution

All 28 unit and integration tests pass cleanly:

```bash
docker exec rag_backend pytest /app/tests
```

```text
============================= test session starts ==============================
collected 28 items

tests/integration/test_api_endpoints.py .......                          [ 25%]
tests/integration/test_pipeline_and_endpoints.py .....                   [ 42%]
tests/unit/test_anti_hallucination.py .....                              [ 60%]
tests/unit/test_chunker_and_loaders.py .                                 [ 64%]
tests/unit/test_feedback_sqlite.py .                                     [ 67%]
tests/unit/test_llm_factory.py ..                                        [ 75%]
tests/unit/test_loaders_and_uploads.py ....                              [ 89%]
tests/unit/test_retrieval_and_store.py ..                                [ 96%]
tests/unit/test_workflow_nodes_and_routing.py .                          [100%]

======================= 28 passed, 14 warnings in 52.52s =======================
```

---

## Quickstart & Installation

### Option 1: Running with Docker (Recommended)

1. **Clone the repository:**
   ```bash
   git clone https://github.com/URK21CS2040/rag-doc-assistant.git
   cd rag-doc-assistant
   ```

2. **Configure Environment:**
   Create a `.env` file in the root directory:
   ```env
   LLM_PROVIDER=groq
   GROQ_API_KEY=gsk_your_groq_api_key_here
   GROQ_MODEL=openai/gpt-oss-20b
   GROQ_FALLBACK_MODEL=qwen/qwen3.8-27b
   TAVILY_API_KEY=tvly-your_tavily_key_here
   CHROMA_PERSIST_DIRECTORY=./data/chroma
   PORT=8000
   ```

3. **Build and start the containers:**
   ```bash
   docker-compose up --build -d
   ```

4. **Access the application:**
   - **Web UI**: `http://localhost`
   - **FastAPI Interactive Docs**: `http://localhost:8000/docs`
   - **Backend Health / Document List**: `http://localhost:8000/documents`

---

### Option 2: Running Locally Without Docker

#### Backend Setup
```bash
cd backend
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
Open `http://localhost:5173` in your browser.

---

## License

This project is licensed under the MIT License.
