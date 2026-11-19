import pytest
from unittest.mock import MagicMock
from app.config import settings
from app.domain.entities import DocumentChunk
from app.workflow.nodes import WorkflowNodes, remove_answer_labels
from app.workflow.state import GraphState

def test_no_hardcoded_answers_when_model_fails():
    mock_vector_store = MagicMock()
    mock_chat_model = MagicMock()
    mock_chat_model.invoke.side_effect = RuntimeError("Groq rate limit or connection timeout")

    nodes = WorkflowNodes(vector_store=mock_vector_store, chat_model=mock_chat_model)

    chunk = DocumentChunk(
        chunk_id="c1",
        document_id="/app/data/sample_docs/Custom_Doc.pdf",
        text="Custom project threshold is 0.42.",
        metadata={"page": 3, "source": "/app/data/sample_docs/Custom_Doc.pdf"},
        score=0.9
    )

    state: GraphState = {
        "question": "What is the critical threshold?",
        "filtered_chunks": [chunk],
        "retrieved_chunks": [chunk],
        "retries": 0,
        "answer": "",
        "sources": []
    }

    result = nodes.generation_node(state)
    answer = result["answer"]

    # Must NOT return hardcoded 0.85 from previous version
    assert "0.85" not in answer
    # Must display verbatim fallback banner
    assert "### AI model unavailable - showing the most relevant passages" in answer
    assert "Custom project threshold is 0.42" in answer
    assert "Custom_Doc.pdf" in answer
    assert "Page 3" in answer


def test_strict_grounding_uncovered_question():
    mock_vector_store = MagicMock()
    mock_chat_model = MagicMock()
    nodes = WorkflowNodes(vector_store=mock_vector_store, chat_model=mock_chat_model)

    state: GraphState = {
        "question": "What is the airspeed velocity of an unladen swallow?",
        "filtered_chunks": [],
        "retrieved_chunks": [],
        "retries": 2,
        "answer": "",
        "sources": []
    }

    orig_strict = settings.strict_grounding
    orig_tavily = settings.tavily_api_key
    try:
        settings.strict_grounding = True
        settings.tavily_api_key = None
        result = nodes.fallback_node(state)
        assert result["answer"] == "This is not covered in the indexed documents."
        assert result["sources"] == []
        assert result["route"] == "not_found"
    finally:
        settings.strict_grounding = orig_strict
        settings.tavily_api_key = orig_tavily


def test_grounded_citations_filter_sources():
    mock_vector_store = MagicMock()
    mock_chat_model = MagicMock()
    # Mock LLM output that only cites [1]
    mock_resp = MagicMock()
    mock_resp.content = "According to the specifications, the maximum capacity is 500 nodes [1]."
    mock_resp.response_metadata = {}
    mock_chat_model.invoke.return_value = mock_resp

    nodes = WorkflowNodes(vector_store=mock_vector_store, chat_model=mock_chat_model)

    chunk1 = DocumentChunk(
        chunk_id="c1",
        document_id="System_Specs.pdf",
        text="The system capacity is 500 nodes.",
        metadata={"page": 1, "source": "System_Specs.pdf"},
        score=0.95
    )
    chunk2 = DocumentChunk(
        chunk_id="c2",
        document_id="Network_Specs.pdf",
        text="Network timeout is 30 seconds.",
        metadata={"page": 5, "source": "Network_Specs.pdf"},
        score=0.80
    )

    state: GraphState = {
        "question": "What is the capacity?",
        "filtered_chunks": [chunk1, chunk2],
        "retrieved_chunks": [chunk1, chunk2],
        "retries": 0,
        "answer": "",
        "sources": []
    }

    result = nodes.generation_node(state)
    # Only chunk1 should be in sources because only [1] was cited
    assert len(result["sources"]) == 1
    assert "System_Specs.pdf" in result["sources"][0]["document_id"]
    assert "Network_Specs.pdf" not in [s["document_id"] for s in result["sources"]]


def test_label_cleanup_no_corruption():
    # Regular "Answers are" should NOT become "s are"
    text1 = "Answers are generated based on document context."
    assert remove_answer_labels(text1) == "Answers are generated based on document context."

    # "Main Answer:" label should be stripped
    text2 = "Main Answer: The learning rate is 0.001."
    assert remove_answer_labels(text2) == "The learning rate is 0.001."

    # "**Detailed Answer:**" should be stripped
    text3 = "**Detailed Answer:**\nSupervised learning uses labeled data."
    assert remove_answer_labels(text3) == "Supervised learning uses labeled data."


def test_bullet_lists_preserved():
    # Ensure bullet lists are never truncated
    list_answer = "Key components:\n- Component A: Primary ingress\n- Component B: Transformer pipeline\n- Component C: Vector index"
    mock_vector_store = MagicMock()
    mock_chat_model = MagicMock()
    mock_resp = MagicMock()
    mock_resp.content = list_answer + " [1]"
    mock_resp.response_metadata = {}
    mock_chat_model.invoke.return_value = mock_resp

    nodes = WorkflowNodes(vector_store=mock_vector_store, chat_model=mock_chat_model)
    chunk = DocumentChunk(
        chunk_id="c1",
        document_id="Doc.pdf",
        text="Components A, B, and C.",
        metadata={"page": 1, "source": "Doc.pdf"},
        score=0.9
    )
    state: GraphState = {
        "question": "List components",
        "filtered_chunks": [chunk],
        "retrieved_chunks": [chunk],
        "retries": 0,
        "answer": "",
        "sources": []
    }
    result = nodes.generation_node(state)
    assert "- Component A: Primary ingress" in result["answer"]
    assert "- Component B: Transformer pipeline" in result["answer"]
    assert "- Component C: Vector index" in result["answer"]

