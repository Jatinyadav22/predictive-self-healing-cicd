from unittest.mock import patch

from src.services.llm_service import generate_explanation


def test_empty_question_returns_empty_string():
    assert generate_explanation("", "some code") == ""


@patch("src.services.llm_service.ollama.chat")
def test_generate_explanation_uses_llm(mock_chat):
    mock_chat.return_value = {
        "message": {
            "content": "The scanner analyzes repository files."
        }
    }

    result = generate_explanation(
        "What does this scanner do?",
        "def scan_repository(): pass",
    )

    assert result == "The scanner analyzes repository files."
    mock_chat.assert_called_once()
