from typing import Any


def search_code(
    index: list[dict[str, Any]],
    query: str,
    max_results: int = 5,
) -> list[dict[str, Any]]:
    """Search indexed repository content using simple keyword relevance."""

    query_terms = {
        term.lower()
        for term in query.split()
        if term.strip()
    }

    if not query_terms:
        return []

    results: list[dict[str, Any]] = []

    for item in index:
        content = item["content"].lower()

        matched_terms = [
            term for term in query_terms
            if term in content
        ]

        if not matched_terms:
            continue

        score = len(matched_terms) / len(query_terms)

        results.append(
            {
                "path": item["path"],
                "score": round(score, 3),
                "matched_terms": sorted(matched_terms),
            }
        )

    results.sort(
        key=lambda item: (-item["score"], item["path"])
    )

    return results[:max_results]
