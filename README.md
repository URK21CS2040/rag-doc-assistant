# RAG-Based Technical Documentation Assistant

A production-ready, Dockerized monorepo implementing a self-corrective Retrieval-Augmented Generation (RAG) system using Python 3.11 (FastAPI, LangGraph, Pydantic v2, ChromaDB, Groq LPU LLM) and React 18 + TypeScript (Vite, Tailwind CSS, Lucide React).

## Architecture Overview
- **Default LLM Engine**: Groq API (`llama-3.3-70b-versatile` via ultra-fast LPU inference at `https://api.groq.com/openai/v1`). Also supports Grok (xAI) and OpenAI.
- **Ingestion Pipeline**: Loads technical Markdown documentation, splits them via recursive character token splitting, generates dense embeddings, and stores them in ChromaDB.
- **LangGraph Workflow**: Implements Query Analysis, Vector Retrieval, LLM Document Grading (self-correction with retry loops), and Answer Generation with grounded citations.
- **FastAPI Backend**: Adheres to strict SOLID principles using typing protocols, dependency injection, and Pydantic v2 validation.
- **React Frontend**: Modern responsive dashboard with real-time Q&A, source citation inspection, document inventory management, and feedback submission.

## How It Works

The system operates as a stateful, self-corrective LangGraph pipeline designed to ensure accurate, hallucination-free answers:

1. **Intent Analysis & Query Expansion**:
   - When a user submits a question, Groq classifies the query's intent (e.g., *Conceptual Guide*, *Code Implementation*, *Comparison Matrix*, *Troubleshooting*).
   - It enriches the prompt with technical synonyms and expanded keywords to maximize semantic search recall.

2. **ChromaDB Vector Retrieval**:
   - The expanded query searches indexed document chunks stored in ChromaDB using vector similarity.

3. **Self-Correction & Relevance Grading**:
   - An LLM grader evaluates each retrieved chunk for relevance against the question.
   - If the relevance score meets the threshold (`>= 0.70`), the chunks proceed to answer generation.
   - If chunks are not sufficiently relevant, the pipeline triggers a self-correction loop, automatically rewriting the search query and retrying (up to 2 retries).

4. **Live Web Search Fallback (Tavily)**:
   - If the required information is not present in local documents after retries, the system seamlessly routes to the Tavily Search API for real-time web results.

5. **Grounded Answer Synthesis & Explainability**:
   - The final answer is generated with source citations and custom-formatted Markdown (tables, syntax-highlighted code blocks with 1-click copy).
   - Under each answer, an interactive **Pipeline Trace Drawer** displays the classified intent, expanded search query, execution path, and relevance confidence score.

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
