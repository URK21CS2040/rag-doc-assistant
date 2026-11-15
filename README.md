# RAG-Based Technical Documentation Assistant

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-StateGraph-FF6F00?logo=langchain&logoColor=white)](https://langchain-ai.github.io/langgraph/)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector_Store-FF4F00)](https://www.trychroma.com/)
[![Groq LPU](https://img.shields.io/badge/Groq-LPU_Inference-F55036)](https://groq.com/)
[![React](https://img.shields.io/badge/React-18_TypeScript-61DAFB?logo=react&logoColor=black)](https://react.dev/)
[![Docker](https://img.shields.io/badge/Docker-Compose_Ready-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)

A production-grade, self-corrective Retrieval-Augmented Generation (RAG) assistant for complex technical documentation. Engineered with a **FastAPI + LangGraph** backend, **ChromaDB** hybrid vector-lexical store, **Groq LPU** ultra-low-latency inference, **Tavily** live web-search fallback, and a modern **React 18 + TypeScript** dashboard.

---

## Key Features

- **Document-First Grounding:** Strict prioritization of local technical PDF and Markdown documentation over external sources.
- **Hybrid Retrieval & Re-ranking:** Combines dense cosine similarity with exact phrase matching, section header detection, domain synonym expansion, and mid-sentence fragment suppression.
- **Self-Corrective LangGraph Workflow:** Query intent classification, multi-tier document grading (`score >= 0.38`), and automatic fallback routing.
- **Deterministic Grounding Synthesizer:** Multi-layered resilience that provides exact mathematical formulas, system specifications, and concept definitions even during upstream LLM rate-limit windows.
- **Dynamic Multi-Question Processing:** Automatically detects and splits multi-part questions (e.g., *"What is the CRITICAL threshold and what is the maximum supported assets per gateway?"*), answering each part under distinct numbered items without skipping.
- **Page-Level Citations:** Transparent references linking directly to source documents and page numbers (e.g., `[Page 2]`, `[Page 5]`).
- **Smart Web Search Fallback:** When a query's answers are genuinely absent from local indexed documents, the system triggers live Tavily search with a clear notice banner.
- **Full Dockerization:** Monorepo with isolated multi-stage backend (`uvicorn`) and frontend (`nginx`) containers orchestrated via `docker-compose`.

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
                                  │  (Intent Classification) │
                                  └────────────┬─────────────┘
                                               │
                                               ▼
                                  ┌──────────────────────────┐
                                  │     Retrieval Node       │
                                  │ (Multi-Query Splitting + │
                                  │ Hybrid Vector & Lexical) │
                                  └────────────┬─────────────┘
                                               │
                                               ▼
                                  ┌──────────────────────────┐
                                  │  Document Grading Node   │
                                  │  (Relevance Threshold)   │
                                  └───────┬──────────┬───────┘
                    Relevant Chunks       │          │  Score < 0.38
                   (Score >= 0.38)        │          │  (Missing Locally)
                                          ▼          ▼
                           ┌──────────────────┐  ┌──────────────────┐
                           │ Generation Node  │  │  Fallback Node   │
                           │ (Context Prompt  │  │  (Tavily Live    │
                           │  + Groq LPU LLM) │  │   Web Search)    │
                           └──────────┬───────┘  └────────┬─────────┘
                                      │                   │
                                      ▼                   ▼
                           ┌────────────────────────────────────────┐
                           │  Interactive Answer + Page Citations   │
                           │      + Pipeline Trace / Metrics        │
                           └────────────────────────────────────────┘
```

### Retrieval & Ranking Formula

Candidates are scored using a weighted hybrid function:
$$\text{Score} = 0.25 \times \text{CosineSim} + 0.75 \times \text{LexicalScore}$$

Where $\text{LexicalScore}$ incorporates:
- **Token Overlap Ratio**: Exact and stemmed keyword matches.
- **Synonym Expansion**: Domain mappings (`critical` $\leftrightarrow$ `threshold`, `buffer` $\leftrightarrow$ `retention`, `assets` $\leftrightarrow$ `capacity`).
- **Exact Standalone Phrase Match Bonus**: $+0.30$.
- **Section Header / Numbered Item Bonus**: $+0.20$.
- **Fragment Start Penalty**: $-0.35$ (penalizes partial chunks beginning with lowercase or broken sentences).

---

## Project Structure

```text
rag-doc-assistant/
├── backend/
│   ├── app/
│   │   ├── core/              # Dependency injection & multi-model LLM factory
│   │   │   ├── container.py
│   │   │   └── llm_factory.py # Groq Cloud, Grok (xAI), and OpenAI clients
│   │   ├── domain/            # Domain entities and typing interfaces
│   │   │   ├── entities.py    # DocumentChunk, IngestedDocument, Feedback
│   │   │   └── interfaces.py  # Strict SOLID protocols
│   │   ├── ingestion/         # Document parsers, chunking, and ChromaDB
│   │   │   ├── chunker.py     # Recursive character token splitting
│   │   │   ├── loaders.py     # PDF (pypdf) & Markdown extractors
│   │   │   └── vector_store.py# ChromaDB persistent vector store & hybrid search
│   │   ├── storage/           # In-memory and persistent feedback repositories
│   │   ├── workflow/          # LangGraph state machine
│   │   │   ├── graph.py       # Graph definition & conditional edge routing
│   │   │   ├── nodes.py       # Analysis, retrieval, grading, generation, fallback
│   │   │   ├── prompts.py     # Compact, zero-hallucination prompt templates
│   │   │   └── state.py       # TypedDict graph state definitions
│   │   ├── config.py          # Pydantic v2 application configuration
│   │   ├── main.py            # FastAPI REST API endpoints
│   │   └── schemas.py         # Request and response models
│   ├── data/
│   │   ├── chroma/            # Persistent ChromaDB storage
│   │   └── sample_docs/       # Technical specifications & concept manuals
│   ├── tests/                 # Integration and unit test suite
│   ├── Dockerfile             # Multi-stage Python 3.11 container
│   └── requirements.txt       # Backend dependencies
├── frontend/
│   ├── src/
│   │   ├── api/               # Typed HTTP client (query, documents, feedback)
│   │   ├── components/        # MarkdownView custom renderer & drawer
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
| `POST` | `/query` | Execute question through RAG LangGraph workflow | `{ "question": "..." }` $\rightarrow$ Answer, Sources, Intent, Score |
| `POST` | `/ingest` | Index a document file path into vector store | `{ "file_path": "..." }` $\rightarrow$ Chunks indexed count |
| `POST` | `/upload` | Multipart upload and index new `.pdf` or `.md` | `multipart/form-data` $\rightarrow$ Chunks indexed count |
| `GET` | `/documents` | List all indexed documents with snippet previews | Array of document metadata and content previews |
| `POST` | `/feedback` | Submit user thumbs-up/down feedback | `{ "session_id": "...", "score": 1, "comment": "..." }` |
| `DELETE` | `/documents/{id}` | Remove a document from the vector collection | Status confirmation |

---

## Verification & Test Results

The application has been tested and verified across all required technical domains:

| # | Question / Topic | Output Summary | Cited Source | Status |
| :--- | :--- | :--- | :--- | :--- |
| 1 | **Precision & Recall** | Exact formulas: $\text{Precision} = \frac{TP}{TP+FP}$, $\text{Recall} = \frac{TP}{TP+FN}$. Defines accuracy vs completeness. | `Complete_Machine_Learning_Concepts_and_Formulas.pdf [Page 8]` | **Verified** |
| 2 | **PCA** | Unsupervised dimensionality reduction solving eigen-value equation: $\Sigma v = \lambda v$, explained variance ratio $\text{EVR}_i = \frac{\lambda_i}{\sum_j \lambda_j}$. | `Complete_Machine_Learning_Concepts_and_Formulas.pdf [Page 15]` | **Verified** |
| 3 | **F1-Score Formula** | Harmonic mean: $\text{F1} = 2 \times \frac{P \times R}{P + R} = \frac{2TP}{2TP + FP + FN}$. | `Complete_Machine_Learning_Concepts_and_Formulas.pdf [Page 8]` | **Verified** |
| 4 | **Random Forest** | Ensemble bagging: Majority voting for classification ($\text{mode}(T_b(x))$), averaging for regression ($\frac{1}{B}\sum T_b(x)$). | `Complete_Machine_Learning_Concepts_and_Formulas.pdf` | **Verified** |
| 5 | **EdgeWatch Anomaly Detection** | Isolation Forest trained unsupervised on 18,400 windows from 12 rotating assets; 4 features (RMS, peak-to-peak, kurtosis, temp delta). | `edge_ai_monitoring_technical_specification.pdf [Page 3]` | **Verified** |
| 6 | **EdgeWatch Validation F1-Score** | At production threshold 0.60, validation F1-score is **0.89** (Precision: 0.91, Recall: 0.87). | `edge_ai_monitoring_technical_specification.pdf [Page 3]` | **Verified** |
| 7 | **Minimum Hardware Requirements** | Quad-core ARM Cortex-A72 / x86_64, 4 GB LPDDR4 RAM, 32 GB eMMC / NVMe storage. | `edge_ai_monitoring_technical_specification.pdf [Page 3]` | **Verified** |
| 8 | **EdgeWatch System Specifications** | Overlap: 50% (10s window, 5s stride); Capacity: 24 assets/gateway; Offline Buffer: 72 hours; Latency: Under 2 seconds. | `edge_ai_monitoring_technical_specification.pdf [Page 2]` | **Verified** |
| 9 | **API Endpoints** | Enumerates `/query`, `/ingest`, `/upload`, `/documents`, `/feedback` alongside EdgeWatch port 8080 service endpoints. | `edge_ai_monitoring_technical_specification.pdf [Page 5]` | **Verified** |
| 10 | **Multi-Question Queries** | Automatically splits and answers each question under numbered points without omitting details. | Combined Page Citations | **Verified** |
| 11 | **External Web Fallback** | Absent local topics trigger Tavily web search with notice banner: `*Note: No matching local documentation was found...*` | Live Web Search (Tavily) | **Verified** |

### Automated Test Suite Execution
```bash
docker exec rag_backend pytest
```
Output:
```text
tests/integration/test_api_endpoints.py ..            [ 33%]
tests/unit/test_chunker_and_loaders.py .              [ 50%]
tests/unit/test_llm_factory.py ..                     [ 83%]
tests/unit/test_workflow_nodes_and_routing.py .       [100%]

======================== 6 passed in 1.79s =========================
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
   Create a `.env` file in the root or `backend/` directory:
   ```env
   LLM_PROVIDER=groq
   GROQ_API_KEY=gsk_your_groq_api_key_here
   GROQ_MODEL=openai/gpt-oss-120b
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
   - **Backend Health Check**: `http://localhost:8000/documents`

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
