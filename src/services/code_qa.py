from src.services.llm_service import generate_explanation
from src.services.semantic_code_search import semantic_search


def answer_code_question(
    repository_path: str,
    question: str,
    max_results: int = 3,
) -> dict:
    if not question.strip():
        return {
            "question": question,
            "results": [],
            "answer": "",
        }

    results = semantic_search(
        repository_path,
        question,
        max_results=max_results,
    )

    context_parts = []

    for result in results:
        path = result["path"]

        try:
            with open(
                f"{repository_path.rstrip('/')}/{path}",
                "r",
                encoding="utf-8",
            ) as file:
                content = file.read()

            context_parts.append(
                f"FILE: {path}\n{content}"
            )
        except (OSError, UnicodeDecodeError):
            continue

    context = "\n\n".join(context_parts)

    answer = generate_explanation(question, context)

    return {
        "question": question,
        "results": results,
        "answer": answer,
    }
