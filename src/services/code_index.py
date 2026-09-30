from pathlib import Path
from typing import Any

from src.services.repository_scanner import (
    IGNORED_DIRECTORIES,
    SUPPORTED_EXTENSIONS,
)


def build_code_index(repository_path: str) -> list[dict[str, Any]]:
    """Build a lightweight searchable index of repository source files."""

    root = Path(repository_path).resolve()

    if not root.exists():
        raise FileNotFoundError(f"Repository not found: {root}")

    index: list[dict[str, Any]] = []

    for path in root.rglob("*"):
        if not path.is_file():
            continue

        if any(part in IGNORED_DIRECTORIES for part in path.parts):
            continue

        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue

        try:
            relative_path = path.relative_to(root)
            content = path.read_text(encoding="utf-8")

            index.append(
                {
                    "path": str(relative_path),
                    "extension": path.suffix.lower(),
                    "content": content,
                }
            )

        except (OSError, UnicodeDecodeError):
            continue

    index.sort(key=lambda item: item["path"])

    return index
