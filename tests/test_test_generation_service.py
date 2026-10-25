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


def test_validate_generated_test_valid_syntax():
    from src.services.test_generation_service import validate_generated_test
    code = (
        "def test_addition():\n"
        "    assert 2 + 2 == 4\n"
        "def test_subtraction():\n"
        "    assert 5 - 2 == 3\n"
    )
    result = validate_generated_test(code)
    assert result["is_valid_syntax"] is True
    assert result["syntax_error"] is None
    assert result["prohibited_imports"] == []
    assert result["duplicate_test_names"] == []
    assert len(result["discovered_test_functions"]) == 2


def test_validate_generated_test_syntax_error():
    from src.services.test_generation_service import validate_generated_test
    code = "def broken_test( assert 1 == 1"
    result = validate_generated_test(code)
    assert result["is_valid_syntax"] is False
    assert result["syntax_error"] is not None


def test_validate_generated_test_flags_prohibited_imports():
    from src.services.test_generation_service import validate_generated_test
    code = (
        "import subprocess\n"
        "import socket\n"
        "def test_dangerous():\n"
        "    assert True\n"
    )
    result = validate_generated_test(code)
    assert result["is_valid_syntax"] is True
    assert "subprocess" in result["prohibited_imports"]
    assert "socket" in result["prohibited_imports"]


def test_validate_generated_test_flags_duplicate_names():
    from src.services.test_generation_service import validate_generated_test
    code = (
        "def test_duplicate():\n"
        "    assert True\n"
        "def test_duplicate():\n"
        "    assert 1 == 1\n"
    )
    result = validate_generated_test(code)
    assert result["is_valid_syntax"] is True
    assert "test_duplicate" in result["duplicate_test_names"]


def test_execute_test_isolated_passing():
    from src.services.test_generation_service import execute_test_isolated
    code = (
        "def test_sandbox_pass():\n"
        "    assert 10 * 10 == 100\n"
    )
    res = execute_test_isolated(code, target_dir="demo_repo", timeout=10)
    assert res["status"] == "PASSED"
    assert res["exit_code"] == 0

