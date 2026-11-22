import asyncio
import logging
from typing import Dict, Any, Optional, List
from langgraph.graph import StateGraph, END
from app.config import settings
from app.workflow.state import GraphState
from app.workflow.nodes import WorkflowNodes

logger = logging.getLogger(__name__)

class WorkflowService:
    def __init__(self, vector_store: Any, chat_model: Any) -> None:
        self._nodes = WorkflowNodes(vector_store=vector_store, chat_model=chat_model)
        self._graph = self._build_graph()
        self._session_history: Dict[str, List[Dict[str, str]]] = {}

    def _build_graph(self) -> StateGraph:
        workflow = StateGraph(GraphState)
        workflow.add_node("query_analysis", self._nodes.query_analysis_node)
        workflow.add_node("retrieval", self._nodes.retrieval_node)
        workflow.add_node("document_grading", self._nodes.document_grading_node)
        workflow.add_node("query_rewrite", self._nodes.query_rewrite_node)
        workflow.add_node("generation", self._nodes.generation_node)
        workflow.add_node("fallback", self._nodes.fallback_node)

        workflow.set_entry_point("query_analysis")
        workflow.add_edge("query_analysis", "retrieval")
        workflow.add_edge("retrieval", "document_grading")

        workflow.add_conditional_edges(
            "document_grading",
            self._decide_next_node,
            {
                "generation": "generation",
                "query_rewrite": "query_rewrite",
                "fallback": "fallback"
            }
        )

        # Loop query_rewrite back into retrieval
        workflow.add_edge("query_rewrite", "retrieval")

        # Grounding & hallucination check edge: if LLM states information is not covered, route to fallback (Tavily)
        workflow.add_conditional_edges(
            "generation",
            self._decide_after_generation,
            {
                "fallback": "fallback",
                "end": END,
            }
        )
        workflow.add_edge("fallback", END)
        return workflow.compile()

    def _decide_after_generation(self, state: GraphState) -> str:
        if state.get("is_fallback_view"):
            logger.info("Generation presented fallback view for unavailable model. Ending workflow without Tavily fallback.")
            return "end"

        answer = state.get("answer", "").strip().lower()
        sources = state.get("sources", [])

        # Sentinels indicating that the LLM concluded the documents do not cover the answer
        refusal_markers = [
            "not covered in the provided documentation",
            "not covered in the indexed",
            "not mentioned in the provided",
            "cannot be found in the provided",
            "cannot be found in the uploaded",
            "not contain information about",
            "does not mention",
            "not provide information about",
        ]
        is_pure_refusal = any(marker in answer for marker in refusal_markers) and (len(sources) == 0 or answer.startswith("this information is not covered"))
        if is_pure_refusal:
            state["tavily_reason"] = "Local documentation contains no information answering this question"
            logger.info("Generation concluded answer is not covered in local documents. Reason: %s. Triggering fallback.", state["tavily_reason"])
            return "fallback"

        # Partial coverage check: If answer contains partial documentation facts and indicates missing details
        if state.get("is_partial") and settings.is_valid_tavily_key():
            state["tavily_reason"] = "Local documentation contains partial information; supplementing missing details via web search"
            logger.info("Generation identified partial local context. Reason: %s. Routing to fallback to supplement.", state["tavily_reason"])
            return "fallback"

        # Ungrounded check: If generation produced text but has 0 supporting citations/sources
        if not sources and state.get("route") == "generation":
            state["tavily_reason"] = "Generation produced ungrounded answer without valid citations"
            logger.info("Generation produced ungrounded answer without valid citations. Reason: %s. Triggering fallback.", state["tavily_reason"])
            return "fallback"

        state["final_source"] = "Local Documentation (PDF)"
        logger.info("[RAG Final] Route: %s | Source: %s | Citations: %d", state.get("route"), state["final_source"], len(sources))
        return "end"

    def _decide_next_node(self, state: GraphState) -> str:
        filtered = state.get("filtered_chunks", [])
        retries = state.get("retries", 0)
        if filtered:
            return "generation"
        if retries < 1:
            return "query_rewrite"
        return "fallback"

    async def run(
        self,
        question: str,
        session_id: Optional[str] = None,
        document_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        sid = session_id or "default"
        history = list(self._session_history.get(sid, []))

        initial_state: GraphState = {
            "question": question,
            "rewritten_query": "",
            "query_intent": "Documentation QA",
            "retrieved_chunks": [],
            "filtered_chunks": [],
            "retries": 0,
            "route": "analysis",
            "document_ids": document_ids,
            "session_id": sid,
            "chat_history": history,
            "answer": "",
            "sources": [],
            "relevance_score": 0.0,
        }
        # Run synchronous LangGraph execution in thread pool to prevent blocking FastAPI event loop
        result = await asyncio.to_thread(self._graph.invoke, initial_state)

        # Record clean turn in session history (keep last 6 turns)
        ans = result.get("answer", "")
        if ans:
            curr_hist = self._session_history.setdefault(sid, [])
            curr_hist.append({"role": "user", "content": question})
            curr_hist.append({"role": "assistant", "content": ans})
            if len(curr_hist) > 6:
                self._session_history[sid] = curr_hist[-6:]

        return result
