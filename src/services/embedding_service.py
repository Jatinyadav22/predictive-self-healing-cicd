from typing import Any

import ollama


EMBEDDING_MODEL = "nomic-embed-text:latest"


def generate_embedding(text: str) -> list[float]:
    """Generate a semantic embedding using the local Ollama model."""

    if not text.strip():
        return []

    response: Any = ollama.embed(
        model=EMBEDDING_MODEL,
        input=text,
    )

    return response["embeddings"][0]
