import ast
from pathlib import Path
from typing import Any


def analyze_python_file(file_path: str | Path) -> dict[str, Any]:
    """Extract structural information from a Python source file."""

    path = Path(file_path)

    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)

    imports: list[str] = []
    functions: list[dict[str, Any]] = []
    classes: list[dict[str, Any]] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)

        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            imports.append(module)

        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions.append(
                {
                    "name": node.name,
                    "line": node.lineno,
                    "end_line": node.end_lineno,
                }
            )

        elif isinstance(node, ast.ClassDef):
            classes.append(
                {
                    "name": node.name,
                    "line": node.lineno,
                    "end_line": node.end_lineno,
                }
            )

    return {
        "file": str(path),
        "imports": sorted(set(imports)),
        "functions": functions,
        "classes": classes,
    }
