import sys
import subprocess
from typing import Optional
from pathlib import Path
from src.config.settings import settings

class PipelineRunner:
    """Runs test suites in a designated repository and captures stdout/stderr."""

    @staticmethod
    def run_tests(repo_path: Optional[Path] = None) -> tuple[int, str]:
        target_dir = Path(repo_path or settings.DEMO_REPO_PATH).resolve()

        if not target_dir.exists():
            return 1, f"Error: target repository path does not exist: {target_dir}"

        try:
            cmd = [sys.executable, "-m", "pytest", "-v", "--tb=short"]
            result = subprocess.run(
                cmd,
                cwd=str(target_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=60
            )
            return result.returncode, result.stdout
        except subprocess.TimeoutExpired:
            return 124, "Pytest execution timed out after 60 seconds."
        except Exception as e:
            return 1, f"Failed to execute pipeline tests: {str(e)}"

pipeline_runner = PipelineRunner()
