from fastapi.testclient import TestClient

from src.main import app


client = TestClient(app)


def test_rag_query_endpoint():
    from src.api import rag

    original_function = rag.generate_rag_answer

    rag.generate_rag_answer = lambda question, max_results: {
        "question": question,
        "answer": "The health endpoint is implemented in src/main.py.",
        "sources": [
            {
                "source": "src/main.py",
                "score": 0.6673,
                "content": 'app.get("/api/health")',
            }
        ],
    }

    try:
        response = client.post(
            "/api/rag/query",
            json={
                "question": "Where is the health endpoint?",
                "max_results": 3,
            },
        )
    finally:
        rag.generate_rag_answer = original_function

    assert response.status_code == 200

    data = response.json()

    assert data["question"] == "Where is the health endpoint?"
    assert "src/main.py" in data["answer"]
    assert len(data["sources"]) == 1
    assert data["sources"][0]["source"] == "src/main.py"


def test_rag_status_endpoint():
    from src.api import rag

    original_function = rag.get_rag_index_status

    rag.get_rag_index_status = lambda: {
        "status": "ready",
        "collection": "repository_knowledge",
        "persist_directory": "data/rag_chroma",
        "embedding_model": "nomic-embed-text:latest",
        "documents": 26,
        "chunks": 42,
    }

    try:
        response = client.get("/api/rag/status")
    finally:
        rag.get_rag_index_status = original_function

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "ready"
    assert data["collection"] == "repository_knowledge"
    assert data["embedding_model"] == "nomic-embed-text:latest"
    assert data["documents"] == 26
    assert data["chunks"] == 42
