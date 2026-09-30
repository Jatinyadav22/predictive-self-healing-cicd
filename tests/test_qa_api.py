from fastapi.testclient import TestClient

from src.main import app


client = TestClient(app)


def test_qa_endpoint_empty_question():
    response = client.post(
        "/api/qa",
        json={
            "question": "",
            "path": ".",
            "max_results": 3,
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["question"] == ""
    assert data["results"] == []
    assert data["answer"] == ""
