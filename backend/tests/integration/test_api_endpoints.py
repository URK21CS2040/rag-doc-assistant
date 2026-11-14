from fastapi.testclient import TestClient

def test_list_documents(client: TestClient) -> None:
    response = client.get("/documents")
    assert response.status_code == 200
    data = response.json()
    assert "documents" in data

def test_feedback_endpoint(client: TestClient) -> None:
    payload = {"session_id": "test_session", "rating": "thumbs_up", "comment": "Great answer"}
    response = client.post("/feedback", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "recorded"
    assert "feedback_id" in data
