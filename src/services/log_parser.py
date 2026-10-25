import re
from typing import Optional

class ParsedError:
    def __init__(
        self,
        error_type: str,
        error_message: str,
        failing_file: Optional[str] = None,
        failing_line: Optional[int] = None,
        failing_symbol: Optional[str] = None,
        failing_test_name: Optional[str] = None,
        stack_trace_snippet: str = ""
    ):
        self.error_type = error_type
        self.error_message = error_message
        self.failing_file = failing_file
        self.failing_line = failing_line
        self.failing_symbol = failing_symbol
        self.failing_test_name = failing_test_name
        self.stack_trace_snippet = stack_trace_snippet

class LogParser:
    """Isolates stack traces, failing assertions, test names, and file locations from build logs."""

    @staticmethod
    def parse_pytest_log(raw_log: str) -> Optional[ParsedError]:
        if not raw_log or not raw_log.strip():
            return None

        failing_file = None
        failing_line = None
        failing_symbol = None
        failing_test_name = None
        error_type = "UNKNOWN"
        error_message = "Unknown pipeline failure"
        stack_snippet_lines = []

        lines = raw_log.splitlines()

        # 1. Look for pytest failure header, e.g. "___ test_calculate_discount ___"
        for line in lines:
            test_match = re.search(r"_{3,}\s+(test_[a-zA-Z0-9_]+)\s+_{3,}", line)
            if test_match:
                failing_test_name = test_match.group(1)
                break

        # 2. Look for Traceback line: both File "...", line X and pytest style path/to/file.py:line:
        traceback_matches = list(re.finditer(r'File\s+"([^"]+)",\s+line\s+(\d+)(?:,\s+in\s+([a-zA-Z0-9_]+))?', raw_log))
        if traceback_matches:
            last_match = traceback_matches[-1]
            raw_path = last_match.group(1)
            failing_file = raw_path.replace("\\", "/").split("/")[-1]
            failing_line = int(last_match.group(2))
            failing_symbol = last_match.group(3)
        else:
            # Pytest format: path/file.py:123: in function_name
            pytest_frame_matches = list(re.finditer(r'([a-zA-Z0-9_\-\./\\]+\.py):(\d+)(?::\s+in\s+([a-zA-Z0-9_]+))?', raw_log))
            if pytest_frame_matches:
                for match in pytest_frame_matches:
                    raw_path = match.group(1).replace("\\", "/").split("/")[-1]
                    failing_line = int(match.group(2))
                    failing_symbol = match.group(3) if match.group(3) else None
                    if raw_path != "conftest.py":
                        failing_file = raw_path

        # If failing file was identified as test_app.py or a test file, target code is app.py
        if failing_file and failing_file.startswith("test_"):
            target_app = failing_file.replace("test_", "")
            failing_file = target_app
        elif not failing_file:
            failing_file = "app.py"

        # 3. Look for explicit Exception lines
        exception_regex = re.compile(r"^([A-Z][a-zA-Z0-9_]*(?:Error|Exception|Failure)):\s*(.*)$")
        for line in reversed(lines):
            stripped = line.strip()
            match = exception_regex.match(stripped)
            if match:
                error_type = match.group(1)
                error_message = match.group(2)
                break
            elif stripped.startswith("E   "):
                e_content = stripped[4:].strip()
                if ":" in e_content:
                    parts = e_content.split(":", 1)
                    error_type = parts[0].strip()
                    error_message = parts[1].strip()
                    break
                else:
                    error_message = e_content

        # 4. Extract compact stack snippet around the failure
        record = False
        for line in lines:
            if "Traceback (most recent call last):" in line or "FAILURES" in line:
                record = True
            if record:
                stack_snippet_lines.append(line)
                if len(stack_snippet_lines) > 40:
                    break

        stack_trace_snippet = "\n".join(stack_snippet_lines) if stack_snippet_lines else raw_log[:1500]

        return ParsedError(
            error_type=error_type,
            error_message=error_message,
            failing_file=failing_file,
            failing_line=failing_line,
            failing_symbol=failing_symbol,
            failing_test_name=failing_test_name,
            stack_trace_snippet=stack_trace_snippet
        )

log_parser = LogParser()
