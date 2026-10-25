from typing import Any

import ollama

from src.services.rag_service import retrieve_repository_context


TEST_GENERATION_MODEL = "qwen2.5:3b"


def _clean_generated_tests(content: str) -> str:
    """Remove common markdown fences from model output."""
    generated = content.strip()

    if generated.startswith("```") and generated.endswith("```"):
        lines = generated.splitlines()

        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]

        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]

        generated = "\n".join(lines).strip()

    return generated


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
repository context below.

The user's request is the PRIMARY scope.

STRICT REQUIREMENTS:

1. Generate tests ONLY for the functionality explicitly requested by the user.

2. Generate at most 3 focused tests.

3. Never generate duplicate test functions.

4. Every test must be a top-level pytest function.
   Never nest one test function inside another.

5. Use ONLY functions, classes, modules, imports, parameters, fixtures,
   constants, filenames, and behavior explicitly supported by the retrieved
   repository context.

6. Never invent pytest fixtures.
   Test function parameters may contain only real fixtures visible in the
   retrieved context.

7. Include every import required by the generated tests.

8. Every import must actually be used.

9. Follow existing repository test patterns whenever test files are present
   in the retrieved context.

10. Every assertion must match the actual data structures and behavior shown
    in the retrieved context.

11. Do not invent expected filenames, directory names, extensions, return
    values, scores, or configuration.

12. Do not generate tests for unrelated modules merely because they appear
    in retrieved context.

13. For a request about the repository scanner, focus only on repository
    scanner behavior and directly required scanner dependencies.

14. Do not generate tests for code search, code Q&A, LLM services, or other
    unrelated components unless explicitly requested.

15. Do not modify production code.

16. The generated result must be valid Python source code.

17. Return ONLY the pytest source code.
    Do not return explanations.
    Do not return headings.
    Do not return Markdown code fences.
    Do not return "Generated tests:".
    Do not append any text after the code.

18. Before returning the answer, internally verify:
    - no duplicate test names
    - no nested test functions
    - required imports are present
    - imports are used
    - no invented fixtures
    - no unrelated tests
    - maximum 3 tests

19. If the retrieved context is insufficient for reliable tests, return only:
    INSUFFICIENT_CONTEXT

User request:
{request}

Retrieved repository context:
{context}

Return the complete pytest source code now:
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

    generated_tests = _clean_generated_tests(
        response["message"]["content"]
    )

    validation = validate_generated_test(generated_tests)

    return {
        "request": request,
        "tests": generated_tests,
        "is_valid": validation["is_valid"],
        "validation_errors": validation["errors"],
        "test_names": validation["test_names"],
        "sources": [
            {
                "source": result["source"],
                "score": result["score"],
                "content": result["content"],
            }
            for result in retrieved
        ],
    }


def validate_generated_test(test_code: str) -> dict[str, Any]:
    """Validates Python syntax, checks for duplicate test functions, and checks for prohibited imports."""
    import ast

    if not test_code or not test_code.strip():
        return {
            "is_valid": False,
            "is_valid_syntax": False,
            "syntax_error": "Empty test candidate code.",
            "errors": ["Test code is empty."],
            "test_names": [],
            "discovered_test_functions": [],
            "duplicate_test_names": [],
            "prohibited_imports": []
        }

    errors = []
    test_names = []
    duplicate_names = []
    prohibited_imports = []

    # 1. AST Syntax validation
    try:
        tree = ast.parse(test_code)
        syntax_error = None
        is_valid_syntax = True
    except SyntaxError as e:
        return {
            "is_valid": False,
            "is_valid_syntax": False,
            "syntax_error": f"Syntax error at line {e.lineno}: {e.msg}",
            "errors": [f"Syntax error at line {e.lineno}: {e.msg}"],
            "test_names": [],
            "discovered_test_functions": [],
            "duplicate_test_names": [],
            "prohibited_imports": []
        }

    # 2. Duplicate test functions check
    seen_names = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name.startswith("test_"):
                if node.name in seen_names:
                    errors.append(f"Duplicate test function detected: '{node.name}'")
                    duplicate_names.append(node.name)
                seen_names.add(node.name)
                test_names.append(node.name)

    if not test_names:
        errors.append("No top-level test functions (starting with 'test_') were found in generated code.")

    # 3. Prohibited dangerous calls/imports check
    prohibited_modules = {"subprocess", "socket", "urllib.request", "telnetlib", "pickle"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in prohibited_modules:
                    errors.append(f"Prohibited security import detected: '{alias.name}'")
                    prohibited_imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module and any(p in node.module for p in prohibited_modules):
                errors.append(f"Prohibited security module import detected: '{node.module}'")
                prohibited_imports.append(node.module)

    return {
        "is_valid": len(errors) == 0,
        "is_valid_syntax": is_valid_syntax,
        "syntax_error": syntax_error,
        "errors": errors,
        "test_names": test_names,
        "discovered_test_functions": test_names,
        "duplicate_test_names": duplicate_names,
        "prohibited_imports": prohibited_imports
    }


def execute_test_isolated(
    test_code: str,
    target_dir: str = "demo_repo",
    timeout: int = 15
) -> dict[str, Any]:
    """Safely executes generated test candidates in an isolated temporary sandbox file with resource bounds."""
    import sys
    import time
    import subprocess
    import tempfile
    from pathlib import Path

    validation = validate_generated_test(test_code)
    if not validation["is_valid"]:
        return {
            "passed": False,
            "status": "VALIDATION_FAILED",
            "exit_code": 1,
            "execution_time_seconds": 0.0,
            "errors": validation["errors"],
            "stdout": "",
            "stderr": "Code rejected by safety validator before execution.",
            "output": "\n".join(validation["errors"]),
            "sandbox_file": "N/A"
        }

    repo_path = Path(target_dir).resolve()
    if not repo_path.exists():
        repo_path = Path(".").resolve()

    tests_dir = repo_path / "tests"
    tests_dir.mkdir(parents=True, exist_ok=True)

    # Create temporary sandbox test file
    temp_suffix = tempfile.mktemp().replace("\\", "/").split("/")[-1].replace("-", "_")
    temp_test_file = tests_dir / f"test_candidate_eval_{temp_suffix}.py"

    start_time = time.time()
    try:
        temp_test_file.write_text(test_code, encoding="utf-8")

        cmd = [sys.executable, "-m", "pytest", "-v", str(temp_test_file.name)]
        proc = subprocess.run(
            cmd,
            cwd=str(tests_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=timeout
        )

        duration = round(time.time() - start_time, 2)
        passed = (proc.returncode == 0)
        return {
            "passed": passed,
            "status": "PASSED" if passed else "FAILED",
            "exit_code": proc.returncode,
            "execution_time_seconds": duration,
            "stdout": proc.stdout,
            "stderr": "",
            "output": proc.stdout,
            "test_names": validation["test_names"],
            "sandbox_file": temp_test_file.name
        }
    except subprocess.TimeoutExpired:
        duration = round(time.time() - start_time, 2)
        return {
            "passed": False,
            "status": "TIMED_OUT",
            "exit_code": 124,
            "execution_time_seconds": duration,
            "stdout": "",
            "stderr": f"Test candidate execution timed out after {timeout} seconds.",
            "output": f"TIMEOUT: Execution exceeded {timeout} seconds resource limit.",
            "sandbox_file": temp_test_file.name
        }
    except Exception as e:
        duration = round(time.time() - start_time, 2)
        return {
            "passed": False,
            "status": "ERROR",
            "exit_code": 1,
            "execution_time_seconds": duration,
            "stdout": "",
            "stderr": str(e),
            "output": str(e),
            "sandbox_file": temp_test_file.name
        }
    finally:
        if temp_test_file.exists():
            try:
                temp_test_file.unlink()
            except Exception:
                pass


