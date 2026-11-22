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

def test_delete_document_endpoint(client: TestClient) -> None:
    response = client.delete("/documents/sample.pdf")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "deleted"
    assert data["document_id"] == "sample.pdf"

def test_delete_all_documents_endpoint(client: TestClient) -> None:
    response = client.delete("/documents")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "chunks_deleted" in data
    assert "files_deleted" in data

def test_ingest_url_rejects_invalid_scheme(client: TestClient) -> None:
    response = client.post("/ingest/url", json={"url": "ftp://example.com/data.txt"})
    assert response.status_code == 422

def test_ingest_url_rejects_localhost_ssrf(client: TestClient) -> None:
    response = client.post("/ingest/url", json={"url": "http://127.0.0.1:8080/secret"})
    assert response.status_code == 422

def test_ingest_url_success_mocked(client: TestClient, monkeypatch) -> None:
    from app.ingestion.loaders import UrlLoader
    sample_html_text = "React is a JavaScript library for building user interfaces. It lets you compose complex UIs from small and isolated pieces of code called components."
    monkeypatch.setattr(UrlLoader, "load", lambda self, url: ("React Documentation", sample_html_text))

    response = client.post("/ingest/url", json={"url": "https://react.dev/learn"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["chunks_indexed"] >= 1
    assert data["title"] == "React Documentation"
    assert data["url"] == "https://react.dev/learn"
