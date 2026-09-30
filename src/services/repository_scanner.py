from pathlib import Path
from typing import Any

from src.services.python_analyzer import analyze_python_file


IGNORED_DIRECTORIES = {
    ".git",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    "node_modules",
    "chroma_db",
    "data",
}


SUPPORTED_EXTENSIONS = {
    ".py",
    ".js",
    ".ts",
    ".java",
    ".cpp",
    ".c",
    ".h",
    ".yaml",
    ".yml",
    ".json",
    ".md",
    ".txt",
    ".sh",
}


def scan_repository(repository_path: str) -> dict[str, Any]:
    """Scan a repository and return structural and code metadata."""

    root = Path(repository_path).resolve()

    if not root.exists():
        raise FileNotFoundError(f"Repository not found: {root}")

    files: list[dict[str, Any]] = []

    for path in root.rglob("*"):
        if not path.is_file():
            continue

        if any(part in IGNORED_DIRECTORIES for part in path.parts):
            continue

        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue

        try:
            relative_path = path.relative_to(root)

            file_info: dict[str, Any] = {
                "path": str(relative_path),
                "extension": path.suffix.lower(),
                "size_bytes": path.stat().st_size,
            }

            if path.suffix.lower() == ".py":
                analysis = analyze_python_file(path)

                file_info["imports"] = analysis["imports"]
                file_info["functions"] = analysis["functions"]
                file_info["classes"] = analysis["classes"]

            files.append(file_info)

        except (OSError, UnicodeDecodeError, SyntaxError):
            continue

    files.sort(key=lambda item: item["path"])

    return {
        "repository": root.name,
        "path": str(root),
        "file_count": len(files),
        "files": files,
    }
