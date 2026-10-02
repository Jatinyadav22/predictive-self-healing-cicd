from pathlib import Path

from src.services.llm_service import generate_explanation


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def _read_code_context(path: str, line_number: int, context_lines: int = 8) -> str:
    """Read a small, safe window of code around the selected Sourcegraph line."""

    repository_root = REPOSITORY_ROOT.resolve()
    requested_path = (repository_root / path).resolve()

    if not requested_path.is_relative_to(repository_root):
        raise ValueError("Invalid repository path")

    if not requested_path.is_file():
        raise FileNotFoundError(f"Repository file not found: {path}")

    lines = requested_path.read_text(encoding="utf-8").splitlines()

    if not lines:
        return ""

    selected_line = max(1, min(line_number, len(lines)))
    start = max(1, selected_line - context_lines)
    end = min(len(lines), selected_line + context_lines)

    return "\n".join(
        f"{number}: {lines[number - 1]}"
        for number in range(start, end + 1)
    )


def explain_sourcegraph_result(
    repository: str,
    path: str,
    line_number: int,
    preview: str,
) -> str:
    """Generate an AI explanation using the actual repository code."""

    code_context = _read_code_context(path, line_number)

    question = (
        f"Explain the code in {path} around line {line_number}. "
        "Describe what the code actually does, how it works, and its role "
        "in the repository. Do not speculate about behavior that is not "
        "supported by the provided code."
    )

    context = (
        f"Repository: {repository}\n"
        f"File: {path}\n"
        f"Selected Sourcegraph line: {line_number}\n"
        f"Sourcegraph preview:\n{preview}\n\n"
        f"Actual repository code context:\n{code_context}"
    )

    return generate_explanation(question, context)
