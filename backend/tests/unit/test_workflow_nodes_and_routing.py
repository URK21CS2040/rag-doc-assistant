from app.workflow.state import GraphState

def test_graph_state_initialization() -> None:
    state: GraphState = {
        "question": "How does FastAPI routing work?",
        "rewritten_query": "",
        "retrieved_chunks": [],
        "filtered_chunks": [],
        "retries": 0,
        "answer": "",
        "sources": []
    }
    assert state["question"] == "How does FastAPI routing work?"
    assert state["retries"] == 0
