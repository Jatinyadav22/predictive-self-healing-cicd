import math
from typing import Any


def cosine_similarity(
    vector_a: list[float],
    vector_b: list[float],
) -> float:
    """Calculate cosine similarity between two vectors."""

    if not vector_a or not vector_b:
        return 0.0

    if len(vector_a) != len(vector_b):
        raise ValueError("Vectors must have the same dimensions")

    dot_product = sum(a * b for a, b in zip(vector_a, vector_b))

    magnitude_a = math.sqrt(sum(a * a for a in vector_a))
    magnitude_b = math.sqrt(sum(b * b for b in vector_b))

    if magnitude_a == 0.0 or magnitude_b == 0.0:
        return 0.0

    return dot_product / (magnitude_a * magnitude_b)


def rank_by_similarity(
    query_vector: list[float],
    documents: list[dict[str, Any]],
    max_results: int = 5,
) -> list[dict[str, Any]]:
    """Rank embedded documents by weighted cosine similarity."""

    results = []

    for document in documents:
        score = cosine_similarity(
            query_vector,
            document["embedding"],
        )

        path = document["path"]

        # Prefer implementation files over test files when
        # semantic relevance is otherwise similar.
        if path.startswith("tests/"):
            weighted_score = score * 0.90
        else:
            weighted_score = score

        results.append(
            {
                "path": path,
                "score": round(weighted_score, 4),
                "semantic_score": round(score, 4),
            }
        )

    results.sort(
        key=lambda item: (-item["score"], item["path"])
    )

    return results[:max_results]
