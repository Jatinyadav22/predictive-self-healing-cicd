from fastapi.testclient import TestClient

from src.main import app


client = TestClient(app)


def test_test_generation_endpoint():
    from src.api import test_generation

    original_function = test_generation.generate_tests

    test_generation.generate_tests = lambda request, max_results: {
        "request": request,
        "tests": (
            "def test_scan_repository_returns_list():\n"
            "    result = scan_repository('.')\n"
            "    assert isinstance(result, list)"
        ),
        "sources": [
            {
                "source": "src/services/repository_scanner.py",
                "score": 0.42,
                "content": "def scan_repository(repository_path): return []",
            }
        ],
    }

    try:
        response = client.post(
            "/api/test-generation/generate",
            json={
                "request": "Generate tests for the repository scanner.",
                "max_results": 1,
            },
        )
    finally:
        test_generation.generate_tests = original_function

    assert response.status_code == 200

    data = response.json()

    assert data["request"] == "Generate tests for the repository scanner."
    assert "def test_scan_repository_returns_list" in data["tests"]
    assert len(data["sources"]) == 1
    assert (
        data["sources"][0]["source"]
        == "src/services/repository_scanner.py"
    )


def test_test_validation_endpoint():
    response = client.post(
        "/api/test-generation/validate",
        json={
            "test_code": "def test_ok():\n    assert 1 == 1\n"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["is_valid_syntax"] is True
    assert "test_ok" in data["discovered_test_functions"]


def test_test_execution_endpoint():
    response = client.post(
        "/api/test-generation/execute",
        json={
            "test_code": "def test_ok():\n    assert True\n",
            "target_dir": "demo_repo",
            "timeout": 10
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "PASSED"
    assert data["exit_code"] == 0

