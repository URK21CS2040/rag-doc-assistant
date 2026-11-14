from typing import Dict, Any
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from app.workflow.state import GraphState
from app.workflow.nodes import WorkflowNodes

class WorkflowService:
    def __init__(self, vector_store: Any, chat_model: ChatOpenAI) -> None:
        self._nodes = WorkflowNodes(vector_store=vector_store, chat_model=chat_model)
        self._graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        workflow = StateGraph(GraphState)
        workflow.add_node("query_analysis", self._nodes.query_analysis_node)
        workflow.add_node("retrieval", self._nodes.retrieval_node)
        workflow.add_node("document_grading", self._nodes.document_grading_node)
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
                "rewrite": "query_analysis",
                "fallback": "fallback"
            }
        )

        workflow.add_edge("generation", END)
        workflow.add_edge("fallback", END)
        return workflow.compile()

    def _decide_next_node(self, state: GraphState) -> str:
        filtered = state["filtered_chunks"]
        retries = state.get("retries", 0)
        if filtered:
            return "generation"
        if retries < 2:
            return "rewrite"
        return "fallback"

    async def run(self, question: str, session_id: str | None = None) -> Dict[str, Any]:
        initial_state: GraphState = {
            "question": question,
            "rewritten_query": "",
            "retrieved_chunks": [],
            "filtered_chunks": [],
            "retries": 0,
            "answer": "",
            "sources": []
        }
        result = self._graph.invoke(initial_state)
        return result
