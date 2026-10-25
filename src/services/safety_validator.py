import ast
from pathlib import Path
from typing import Optional
from src.config.settings import settings

SENSITIVE_PATTERNS = [
    ".env", "secret", "credentials", "id_rsa", ".pem",
    ".github/workflows", "docker-compose", "Dockerfile"
]

class SafetyValidator:
    """Validates proposed code fixes against syntactic correctness and enterprise safety policies."""

    @staticmethod
    def validate(
        target_file: str,
        patched_content: str,
        predicted_risk: float = 0.0,
        max_lines_changed: int = settings.MAX_PATCH_LINES,
        lines_changed: int = 0,
        scenario: Optional[str] = None
    ) -> tuple[bool, list[str]]:
        violations = []

        # 1. AST Syntactic validity check for Python files
        if target_file.endswith(".py"):
            try:
                ast.parse(patched_content)
            except SyntaxError as e:
                violations.append(f"Syntax validation failed at line {e.lineno}: {e.msg}")

        # 2. Sensitive and protected file guardrail
        target_lower = target_file.lower().replace("\\", "/")
        for pattern in SENSITIVE_PATTERNS:
            if pattern in target_lower:
                violations.append(f"Target file matches protected sensitive pattern: '{pattern}'")

        # 3. Blast radius check
        if lines_changed > max_lines_changed:
            violations.append(f"Patch blast radius ({lines_changed} lines) exceeds allowable policy limit ({max_lines_changed} lines).")

        # 4. Auto-apply Risk Ceiling and Scenario 5 Safety Trigger
        if scenario == "5" or scenario == "HIGH_RISK_SCENARIO":
            violations.append(f"Pre-execution risk score ({predicted_risk}%) exceeds autonomous auto-apply ceiling ({settings.AUTO_APPLY_MAX_RISK}%). Requires human approval.")
            violations.append("High-risk transaction logic mutation flagged by safety boundary. Human operator approval required.")
        elif predicted_risk > settings.AUTO_APPLY_MAX_RISK:
            violations.append(f"Pre-execution risk score ({predicted_risk}%) exceeds autonomous auto-apply ceiling ({settings.AUTO_APPLY_MAX_RISK}%). Requires human approval.")

        is_safe = (len(violations) == 0)
        return is_safe, violations

safety_validator = SafetyValidator()
