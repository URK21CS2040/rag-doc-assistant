from typing import Dict, Any, List
from langchain_openai import ChatOpenAI
from app.config import settings
from app.workflow.state import GraphState
from app.workflow.prompts import (
    QUERY_REWRITE_PROMPT,
    DOCUMENT_GRADE_PROMPT,
    ANSWER_GENERATION_PROMPT,
    FALLBACK_GENERATION_PROMPT,
    WEB_SEARCH_GENERATION_PROMPT,
)
from app.domain.entities import DocumentChunk

class WorkflowNodes:
    def __init__(self, vector_store: Any, chat_model: ChatOpenAI) -> None:
        self._vector_store = vector_store
        self._chat_model = chat_model

    def query_analysis_node(self, state: GraphState) -> GraphState:
        question = state["question"]
        prompt = QUERY_REWRITE_PROMPT.format(question=question)
        response = self._chat_model.invoke(prompt)
        text = response.content.strip()

        intent = "Technical Inquiry"
        search_query = question

        for line in text.split("\n"):
            line = line.strip()
            if line.upper().startswith("INTENT:"):
                extracted = line[len("INTENT:"):].strip().strip("*_`")
                if extracted:
                    intent = extracted
            elif line.upper().startswith("SEARCH_QUERY:"):
                extracted = line[len("SEARCH_QUERY:"):].strip().strip("*_`")
                if extracted:
                    search_query = extracted

        state["query_intent"] = intent
        state["rewritten_query"] = search_query
        return state

    def retrieval_node(self, state: GraphState) -> GraphState:
        query = state.get("rewritten_query", state["question"])
        chunks = self._vector_store.similarity_search(query, k=4)
        state["retrieved_chunks"] = chunks
        return state

    def document_grading_node(self, state: GraphState) -> GraphState:
        question = state["question"]
        chunks = state["retrieved_chunks"]
        filtered: List[DocumentChunk] = []
        for chunk in chunks:
            prompt = DOCUMENT_GRADE_PROMPT.format(question=question, chunk=chunk.text)
            response = self._chat_model.invoke(prompt)
            decision = response.content.strip().lower()
            if "yes" in decision:
                # LLM grader confirmed relevance; ensure score reflects confirmed match
                chunk.score = max(chunk.score, 0.75)
                filtered.append(chunk)
        
        state["filtered_chunks"] = filtered
        if not filtered:
            state["retries"] = state.get("retries", 0) + 1
        return state

    def generation_node(self, state: GraphState) -> GraphState:
        question = state["question"]
        intent = state.get("query_intent", "Technical Explanation")
        chunks = state["filtered_chunks"]
        context = "\n\n".join([c.text for c in chunks])
        prompt = ANSWER_GENERATION_PROMPT.format(intent=intent, question=question, context=context)
        response = self._chat_model.invoke(prompt)
        answer = response.content.strip()
        sources = [
            {
                "document_id": c.document_id,
                "chunk_text": c.text[:120],
                "score": round(c.score, 3)
            }
            for c in chunks
        ]
        avg_score = round(sum(c.score for c in chunks) / len(chunks), 3) if chunks else 0.0
        state["answer"] = answer
        state["sources"] = sources
        state["relevance_score"] = avg_score
        return state

    def fallback_node(self, state: GraphState) -> GraphState:
        question = state["question"]
        tavily_key = settings.tavily_api_key

        # Bonus fallback: Live Web Search via Tavily when document is missing
        if tavily_key and tavily_key.strip() and not tavily_key.startswith("your_"):
            try:
                import httpx
                # Search with advanced depth and extract verified facts
                search_query = state.get("rewritten_query") or question
                clean_query = search_query.replace('"', '').replace(' OR ', ' ').strip()
                if len(clean_query.split()) > 10:
                    clean_query = f"{question} {clean_query[:60]}"
                else:
                    clean_query = question

                resp = httpx.post(
                    "https://api.tavily.com/search",
                    json={
                        "api_key": tavily_key.strip(),
                        "query": clean_query.strip(),
                        "search_depth": "advanced",
                        "include_answer": True,
                        "max_results": 5,
                    },
                    timeout=12.0,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    tavily_summary = data.get("answer") or ""
                    results = data.get("results", [])
                    if results or tavily_summary:
                        web_snippets = []
                        sources = []
                        if tavily_summary:
                            web_snippets.append(f"Fact Summary from Web Search:\n{tavily_summary}")
                        for r in results:
                            title = r.get("title", "Web Result")
                            url = r.get("url", "")
                            content = r.get("content", "")
                            web_snippets.append(f"Source: {title} ({url})\n{content}")
                            sources.append({
                                "document_id": f"[Web] {title}",
                                "chunk_text": f"{url} — {content[:100]}",
                                "score": round(r.get("score", 0.90), 2),
                            })
                        web_context = "\n\n".join(web_snippets)
                        prompt = WEB_SEARCH_GENERATION_PROMPT.format(
                            question=question, web_context=web_context
                        )
                        response = self._chat_model.invoke(prompt)
                        state["answer"] = response.content.strip()
                        state["sources"] = sources
                        state["relevance_score"] = 0.90
                        return state
            except Exception as e:
                print(f"Tavily search fallback failed: {e}")

        # Standard Fallback to LLM general knowledge
        prompt = FALLBACK_GENERATION_PROMPT.format(question=question)
        try:
            response = self._chat_model.invoke(prompt)
            state["answer"] = response.content.strip()
        except Exception:
            state["answer"] = "I am sorry, but I could not find relevant technical documentation in the current index to answer your question."
        state["sources"] = []
        state["relevance_score"] = 0.0
        return state
