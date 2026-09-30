from typing import Any

import ollama


LLM_MODEL = "qwen2.5:3b"


def generate_explanation(question: str, context: str) -> str:
    if not question.strip():
        return ""

    prompt = f"""
You are an AI code assistant analyzing a software repository.

Answer the user's question using ONLY the provided repository context.
If the context does not contain enough information, say that clearly.
Do not invent files, functions, or behavior.

User question:
{question}

Repository context:
{context}

Give a concise, technically accurate explanation.
""".strip()

    response: Any = ollama.chat(
        model=LLM_MODEL,
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
    )

    return response["message"]["content"].strip()
