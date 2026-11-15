from typing import Dict, Any, List, Optional
from concurrent.futures import ThreadPoolExecutor
import re
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


def ensure_complete_ending(text: str) -> str:
    """
    Cleans up any dangling/cut-off incomplete sentences or bullet points at the end of the text.
    If the text ends abruptly without terminal punctuation, it trims the dangling line.
    """
    if not text:
        return text
    cleaned = text.strip()
    terminal_markers = ('.', '!', '?', '```', '|', '\\]', '$$', ':', '**')
    if cleaned.endswith(terminal_markers):
        return cleaned

    lines = cleaned.split("\n")
    while lines:
        last_line = lines[-1].strip()
        if not last_line:
            lines.pop()
            continue
        if last_line.endswith(terminal_markers):
            break
        matches = list(re.finditer(r'([.!?])(?:\s+|$)', last_line))
        if matches:
            last_idx = matches[-1].end(1)
            lines[-1] = last_line[:last_idx].strip()
            break
        else:
            lines.pop()

    result = "\n".join(lines).strip()
    return result if result else cleaned

class WorkflowNodes:
    def __init__(self, vector_store: Any, chat_model: ChatOpenAI) -> None:
        self._vector_store = vector_store
        self._chat_model = chat_model

    def query_analysis_node(self, state: GraphState) -> GraphState:
        question = state["question"]
        prompt = QUERY_REWRITE_PROMPT.format(question=question)
        intent = "Educational & Conceptual"
        search_query = question

        try:
            response = self._chat_model.invoke(prompt)
            text = response.content.strip() if hasattr(response, "content") else str(response).strip()
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
        except Exception as e:
            print(f"query_analysis_node fallback due to: {e}")
            q_lower = question.lower()
            if any(k in q_lower for k in ["who is", "who was", "captain", "ceo", "president", "latest version", "current status"]):
                intent = "Fact & Status Lookup"
            elif any(k in q_lower for k in ["is ", "is it", "has ", "confirmed", "are there", "does it contain"]):
                intent = "Confirmation & Verification"
            elif any(k in q_lower for k in ["vs", "difference between", "compare", "distinguish"]):
                intent = "Comparison & Matrix"
            elif any(k in q_lower for k in ["workflow", "architecture", "how does", "pipeline", "why is"]):
                intent = "Analytical & Workflow"
            else:
                intent = "Educational & Conceptual"
            search_query = question

        state["query_intent"] = intent
        state["rewritten_query"] = search_query
        return state

    def retrieval_node(self, state: GraphState) -> GraphState:
        query = state.get("rewritten_query", state["question"])
        chunks = self._vector_store.similarity_search(query, k=6)
        state["retrieved_chunks"] = chunks
        return state

    def document_grading_node(self, state: GraphState) -> GraphState:
        question = state["question"]
        chunks = state["retrieved_chunks"]
        if not chunks:
            state["filtered_chunks"] = []
            state["retries"] = state.get("retries", 0) + 1
            return state

        # If the highest chunk score is below threshold, local docs are not relevant
        max_score = max((c.score for c in chunks), default=0.0)
        if max_score < 0.42:
            state["filtered_chunks"] = []
            state["retries"] = 99  # Skip rewrite loops, route directly to fallback
            return state

        # Only evaluate candidates with score >= 0.42 (top 4 max)
        candidates = [c for c in chunks if c.score >= 0.42][:4]
        filtered: List[DocumentChunk] = []

        def grade_chunk(chunk: DocumentChunk) -> Optional[DocumentChunk]:
            # Solid similarity match: accept without extra LLM call
            if chunk.score >= 0.65:
                return chunk

            prompt = DOCUMENT_GRADE_PROMPT.format(question=question, chunk=chunk.text)
            try:
                response = self._chat_model.invoke(prompt)
                decision = response.content.strip().lower() if hasattr(response, "content") else str(response).strip().lower()
                if ":" in decision:
                    decision = decision.split(":")[-1].strip()
                decision = decision.strip().strip(".!*_` \n\t")
                if decision == "yes" or decision.startswith("yes"):
                    chunk.score = max(chunk.score, 0.75)
                    return chunk
            except Exception as e:
                print(f"Error grading chunk: {e}")
                if chunk.score >= 0.50:
                    return chunk
            return None

        with ThreadPoolExecutor(max_workers=min(len(candidates), 4)) as executor:
            graded_results = list(executor.map(grade_chunk, candidates))

        filtered = [c for c in graded_results if c is not None]
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
        try:
            response = self._chat_model.invoke(prompt)
            answer = response.content.strip() if hasattr(response, "content") else str(response).strip()
        except Exception as e:
            print(f"Error during answer generation: {e}")
            answer = "I am sorry, but an error occurred while contacting the model. Please submit your question again."

        sources = [
            {
                "document_id": c.document_id,
                "chunk_text": c.text[:120],
                "score": round(c.score, 3)
            }
            for c in chunks
        ]
        avg_score = round(sum(c.score for c in chunks) / len(chunks), 3) if chunks else 0.0
        state["answer"] = ensure_complete_ending(answer)
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
                # Always use the user's raw question for web search to prevent vector query rewrites from injecting outdated years (like '2024')
                clean_query = question.strip()

                # Detect if query involves current status, leadership, recent trades, or time-sensitive events
                time_keywords = [
                    "current", "captain", "latest", "now", "today", "recent", "who is",
                    "new", "trade", "traded", "coach", "ceo", "president", "minister", "leader", "squad"
                ]
                is_time_sensitive = any(kw in clean_query.lower() for kw in time_keywords)

                results = []
                tavily_summaries = []

                # Step 1: When time-sensitive, fetch breaking/recent news first to avoid outdated static pages
                if is_time_sensitive:
                    try:
                        resp_news = httpx.post(
                            "https://api.tavily.com/search",
                            json={
                                "api_key": tavily_key.strip(),
                                "query": f"{clean_query} latest news updates trade",
                                "topic": "news",
                                "search_depth": "advanced",
                                "include_answer": True,
                                "max_results": 5,
                            },
                            timeout=10.0,
                        )
                        if resp_news.status_code == 200:
                            data_news = resp_news.json()
                            if data_news.get("answer"):
                                tavily_summaries.append(f"Latest News Summary:\n{data_news['answer']}")
                            for r in data_news.get("results", []):
                                results.append(r)
                    except Exception as e:
                        print(f"Tavily news search failed: {e}")

                # Step 2: Comprehensive advanced search for player/technical profiles
                try:
                    resp_gen = httpx.post(
                        "https://api.tavily.com/search",
                        json={
                            "api_key": tavily_key.strip(),
                            "query": f"{clean_query} latest",
                            "search_depth": "advanced",
                            "include_answer": True,
                            "max_results": 4,
                        },
                        timeout=10.0,
                    )
                    if resp_gen.status_code == 200:
                        data_gen = resp_gen.json()
                        if data_gen.get("answer"):
                            tavily_summaries.append(f"Fact Summary:\n{data_gen['answer']}")
                        for r in data_gen.get("results", []):
                            if not any(existing.get("url") == r.get("url") for existing in results):
                                results.append(r)
                except Exception as e:
                    print(f"Tavily general search failed: {e}")

                if results or tavily_summaries:
                    web_snippets = []
                    sources = []
                    for s in tavily_summaries:
                        web_snippets.append(s)
                    for r in results[:5]:
                        title = r.get("title", "Web Result")
                        url = r.get("url", "")
                        content = r.get("content", "")
                        published = r.get("published_date")
                        date_str = f" [Date: {published}]" if published else ""
                        web_snippets.append(f"Source: {title}{date_str} ({url})\n{content}")
                        sources.append({
                            "document_id": f"[Web] {title}",
                            "chunk_text": f"{url} — {content[:100]}",
                            "score": round(r.get("score", 0.90), 2),
                        })
                    web_context = "\n\n".join(web_snippets)
                    intent = state.get("query_intent", "Fact & Status Lookup")
                    prompt = WEB_SEARCH_GENERATION_PROMPT.format(
                        intent=intent, question=question, web_context=web_context
                    )
                    response = self._chat_model.invoke(prompt)
                    ans_text = response.content.strip() if hasattr(response, "content") else str(response).strip()
                    state["answer"] = ensure_complete_ending(ans_text)
                    state["sources"] = sources
                    state["relevance_score"] = 0.90
                    return state
            except Exception as e:
                print(f"Tavily search fallback failed: {e}")

        # Standard Fallback to LLM general knowledge
        intent = state.get("query_intent", "Educational & Conceptual")
        prompt = FALLBACK_GENERATION_PROMPT.format(intent=intent, question=question)
        try:
            response = self._chat_model.invoke(prompt)
            ans_text = response.content.strip() if hasattr(response, "content") else str(response).strip()
            state["answer"] = ensure_complete_ending(ans_text)
        except Exception:
            state["answer"] = "I am sorry, but I could not find relevant technical documentation in the current index to answer your question."
        state["sources"] = []
        state["relevance_score"] = 0.0
        return state
