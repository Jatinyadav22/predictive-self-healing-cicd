from src.services.python_analyzer import analyze_python_file
from src.services.repository_scanner import scan_repository


def test_python_analyzer_detects_function_and_import():
    result = analyze_python_file("src/main.py")

    assert "fastapi" in result["imports"]
    assert any(
        function["name"] == "health_check"
        for function in result["functions"]
    )


def test_repository_scanner_detects_project_files():
    result = scan_repository(".")

    paths = {file["path"] for file in result["files"]}

    assert "src/main.py" in paths
    assert "src/services/python_analyzer.py" in paths
    assert "src/services/repository_scanner.py" in paths


def test_repository_scanner_extracts_python_structure():
    result = scan_repository(".")

    main_file = next(
        file for file in result["files"]
        if file["path"] == "src/main.py"
    )

    assert "fastapi" in main_file["imports"]
    assert any(
        function["name"] == "health_check"
        for function in main_file["functions"]
    )
