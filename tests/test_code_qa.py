from unittest.mock import patch

from src.services.code_qa import answer_code_question


def test_empty_question_returns_empty_response():
    result = answer_code_question(".", "")

    assert result["question"] == ""
    assert result["results"] == []
    assert result["answer"] == ""


@patch("src.services.code_qa.generate_explanation")
@patch("src.services.code_qa.semantic_search")
def test_code_qa_combines_retrieval_and_llm(mock_search, mock_explanation):
    mock_search.return_value = [
        {
            "path": "src/example.py",
            "score": 0.9,
            "semantic_score": 0.9,
        }
    ]

    mock_explanation.return_value = "The example module handles repository analysis."

    result = answer_code_question(
        ".",
        "What does the example module do?",
        max_results=1,
    )

    assert result["answer"] == "The example module handles repository analysis."
    assert len(result["results"]) == 1
    assert result["results"][0]["path"] == "src/example.py"

    mock_search.assert_called_once_with(
        ".",
        "What does the example module do?",
        max_results=1,
    )

    mock_explanation.assert_called_once()
