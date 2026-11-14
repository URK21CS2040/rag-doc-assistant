# RAG-Based Technical Documentation Assistant

A production-ready, Dockerized monorepo implementing a self-corrective Retrieval-Augmented Generation (RAG) system using Python 3.11 (FastAPI, LangGraph, Pydantic v2, ChromaDB, Groq LPU LLM) and React 18 + TypeScript (Vite, Tailwind CSS, Lucide React).

## Architecture Overview
- **Default LLM Engine**: Groq API (`llama-3.3-70b-versatile` via ultra-fast LPU inference at `https://api.groq.com/openai/v1`). Also supports Grok (xAI) and OpenAI.
- **Ingestion Pipeline**: Loads technical Markdown documentation, splits them via recursive character token splitting, generates dense embeddings, and stores them in ChromaDB.
- **LangGraph Workflow**: Implements Query Analysis, Vector Retrieval, LLM Document Grading (self-correction with retry loops), and Answer Generation with grounded citations.
- **FastAPI Backend**: Adheres to strict SOLID principles using typing protocols, dependency injection, and Pydantic v2 validation.
- **React Frontend**: Modern responsive dashboard with real-time Q&A, source citation inspection, document inventory management, and feedback submission.

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
