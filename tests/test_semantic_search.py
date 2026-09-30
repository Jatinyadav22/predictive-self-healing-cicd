from src.services.semantic_search import cosine_similarity, rank_by_similarity


def test_cosine_similarity_identical_vectors():
    assert cosine_similarity([1, 0], [1, 0]) == 1.0


def test_cosine_similarity_orthogonal_vectors():
    assert cosine_similarity([1, 0], [0, 1]) == 0.0


def test_test_files_receive_lower_weight():
    query = [1, 0]

    documents = [
        {"path": "tests/example.py", "embedding": [1, 0]},
        {"path": "src/example.py", "embedding": [0.95, 0.1]},
    ]

    results = rank_by_similarity(query, documents, max_results=2)

    assert results[0]["path"] == "src/example.py"
    assert results[0]["score"] > results[1]["score"]
