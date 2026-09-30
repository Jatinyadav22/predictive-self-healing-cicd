from typing import Any

from src.services.code_index import build_code_index
from src.services.embedding_service import generate_embedding
from src.services.semantic_search import rank_by_similarity


def semantic_search(
    repository_path: str,
    query: str,
    max_results: int = 5,
) -> list[dict[str, Any]]:
    """Search repository files using semantic embeddings."""

    if not query.strip():
        return []

    index = build_code_index(repository_path)
    query_vector = generate_embedding(query)

    documents: list[dict[str, Any]] = []

    for item in index:
        content = item["content"]

        if not content.strip():
            continue

        document_vector = generate_embedding(content)

        documents.append(
            {
                "path": item["path"],
                "embedding": document_vector,
            }
        )

    return rank_by_similarity(
        query_vector,
        documents,
        max_results=max_results,
    )
