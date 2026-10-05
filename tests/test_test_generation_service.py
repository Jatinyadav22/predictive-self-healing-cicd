from unittest.mock import patch

from src.services.test_generation_service import generate_tests


def test_empty_request_returns_empty_response():
    result = generate_tests("")

    assert result["request"] == ""
    assert result["tests"] == ""
    assert result["sources"] == []


@patch("src.services.test_generation_service.ollama.chat")
@patch("src.services.test_generation_service.retrieve_repository_context")
def test_generate_tests_uses_rag_context_and_llm(
    mock_retrieve,
    mock_chat,
):
    mock_retrieve.return_value = [
        {
            "source": "src/services/repository_scanner.py",
            "score": 0.42,
            "content": "def scan_repository(repository_path): return []",
        }
    ]

    mock_chat.return_value = {
        "message": {
            "content": (
                "def test_scan_repository_returns_list():\n"
                "    result = scan_repository('.')\n"
                "    assert isinstance(result, list)"
            )
        }
    }

    result = generate_tests(
        "Generate tests for the repository scanner.",
        max_results=1,
    )

    assert "def test_scan_repository_returns_list" in result["tests"]
    assert len(result["sources"]) == 1
    assert (
        result["sources"][0]["source"]
        == "src/services/repository_scanner.py"
    )

    mock_retrieve.assert_called_once_with(
        "Generate tests for the repository scanner.",
        max_results=1,
    )

    mock_chat.assert_called_once()
