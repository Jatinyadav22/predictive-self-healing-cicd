from src.services.code_index import build_code_index
from src.services.code_search import search_code


def test_code_search_finds_repository_scanner():
    index = build_code_index(".")

    results = search_code(index, "repository scanner")

    assert results
    assert results[0]["path"] == "src/api/repository.py"
    assert results[0]["score"] == 1.0


def test_code_search_returns_empty_for_blank_query():
    index = build_code_index(".")

    results = search_code(index, "")

    assert results == []


def test_code_search_respects_max_results():
    index = build_code_index(".")

    results = search_code(index, "repository", max_results=2)

    assert len(results) <= 2
