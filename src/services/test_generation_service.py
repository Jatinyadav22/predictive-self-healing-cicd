from typing import Any

import ollama

from src.services.rag_service import retrieve_repository_context


TEST_GENERATION_MODEL = "qwen2.5:3b"


def generate_tests(
    request: str,
    max_results: int = 5,
) -> dict[str, object]:
    """Generate repository-grounded pytest tests from RAG context."""

    if not request.strip():
        return {
            "request": request,
            "tests": "",
            "sources": [],
        }

    retrieved = retrieve_repository_context(
        request,
        max_results=max_results,
    )

    if not retrieved:
        return {
            "request": request,
            "tests": "",
            "sources": [],
        }

    context_parts = []

    for index, result in enumerate(retrieved, start=1):
        context_parts.append(
            f"[Source {index}]\n"
            f"File: {result['source']}\n"
            f"Content:\n{result['content']}"
        )

    context = "\n\n".join(context_parts)

    prompt = f"""
You are an AI test-generation assistant for a Python software repository.

Generate pytest tests for the user's request using ONLY the retrieved
repository context provided below.

Rules:
- Generate tests only for behavior supported by the retrieved context.
- Do not invent files, functions, classes, endpoints, parameters, or behavior.
- Use pytest syntax.
- Prefer focused, deterministic tests.
- Reuse the repository's existing naming and structure when supported.
- Do not modify production code.
- If the retrieved context is insufficient to generate a reliable test,
  clearly say so instead of inventing implementation details.
- Return the generated pytest code first.
- After the code, provide a short explanation of what the tests validate.

User request:
{request}

Retrieved repository context:
{context}

Generated tests:
""".strip()

    response: Any = ollama.chat(
        model=TEST_GENERATION_MODEL,
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
    )

    generated_tests = response["message"]["content"].strip()

    return {
        "request": request,
        "tests": generated_tests,
        "sources": [
            {
                "source": result["source"],
                "score": result["score"],
                "content": result["content"],
            }
            for result in retrieved
        ],
    }
