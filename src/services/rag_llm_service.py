from typing import Any

import ollama


RAG_LLM_MODEL = "qwen2.5:3b"


def generate_rag_response(
    question: str,
    context: str,
) -> str:
    """Generate a repository-grounded answer from retrieved RAG context."""

    if not question.strip():
        return ""

    if not context.strip():
        return "No relevant repository context was retrieved."

    prompt = f"""
You are the RAG assistant for a software repository.

Answer the user's question using ONLY the retrieved repository context
provided below.

Rules:
- Do not invent files, functions, behavior, or configuration.
- Do not rely on information outside the retrieved context.
- If the context is insufficient to answer the question, say so clearly.
- Mention relevant file names when useful.
- Keep the answer concise and technically accurate.

User question:
{question}

Retrieved repository context:
{context}

Answer:
""".strip()

    response: Any = ollama.chat(
        model=RAG_LLM_MODEL,
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
    )

    return response["message"]["content"].strip()
