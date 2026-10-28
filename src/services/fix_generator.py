import re
import difflib
from pathlib import Path
from typing import Optional
from src.config.settings import settings
from src.models.schemas import FailureClassification, RCAAnalysis, FixProposal
from src.services.ollama_client import ollama_client

class FixGenerator:
    """Generates targeted, minimal candidate diffs using AST analysis and local LLM."""

    def generate_fix(
        self,
        classification: FailureClassification,
        rca: RCAAnalysis,
        repo_path: Optional[Path] = None
    ) -> Optional[FixProposal]:
        repo_dir = Path(repo_path or settings.DEMO_REPO_PATH).resolve()

        # Find target file
        candidate_files = []
        if classification.failing_file:
            candidate_files.append(repo_dir / classification.failing_file)
            candidate_files.append(repo_dir / f"{classification.failing_file}.py")

        target_path = None
        for p in candidate_files:
            if p.is_file():
                target_path = p
                break

        if not target_path or not target_path.exists():
            target_path = repo_dir / "app.py"
            if not target_path.exists():
                return None

        try:
            original_content = target_path.read_text(encoding="utf-8")
        except Exception:
            return None

        rel_target = str(target_path.relative_to(repo_dir)).replace("\\", "/")

        target_symbol = classification.failing_symbol
        old_function_code = ""
        target_node = None

        # Parse AST of target file to map all defined functions
        defined_functions = {}
        try:
            import ast
            tree = ast.parse(original_content)
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    defined_functions[node.name] = node
        except Exception:
            defined_functions = {}

        # Prioritize function mentioned in RCA or error message if available
        search_text = f"{rca.root_cause_summary} {rca.fix_strategy} {classification.error_message}"
        for fn_name in defined_functions:
            if fn_name in search_text:
                target_symbol = fn_name
                break

        if target_symbol and target_symbol in defined_functions:
            target_node = defined_functions[target_symbol]
            orig_lines = original_content.splitlines(keepends=True)
            old_function_code = "".join(orig_lines[target_node.lineno - 1:target_node.end_lineno])

        if old_function_code and target_node:
            prompt = f"""You are an expert Python software engineer.
Fix the bug in this Python function so that all unit tests pass.
- Remove any erroneous arithmetic offsets, unexpected additions, or subtractions (such as '+ 5.0', '- 5.0', or '+ 5') from calculations.
- Ensure standard financial formulas produce the exact expected result (e.g. 'final_price = total - discount_amount').
- Fix any syntax errors or unclosed parentheses.
Output ONLY the complete corrected function definition. Do NOT output markdown code fences, notes, or explanations.

ERROR: {classification.error_message}
FAILING TEST: {classification.failing_test_name or 'Unit Test'}
{classification.stack_trace[:300]}

RCA: {rca.root_cause_summary}
STRATEGY: {rca.fix_strategy}

ORIGINAL FUNCTION:
{old_function_code}

CORRECTED FUNCTION:"""

            raw_fixed = ollama_client.generate(
                prompt=prompt,
                model=settings.LLM_CODE_MODEL,
                temperature=0.1,
                num_predict=180,
                stop=["\ndef ", "\nclass "]
            )
            clean_fixed = raw_fixed.strip()
            if "```" in clean_fixed:
                clean_fixed = re.sub(r"```(?:python)?\s*\n?", "", clean_fixed)
                clean_fixed = re.sub(r"\n?```$", "", clean_fixed).strip()

            # Use AST to isolate exactly the target function from LLM output, discarding any partial text
            isolated_function = ""
            lines = clean_fixed.splitlines()
            for i in range(len(lines), 0, -1):
                candidate = "\n".join(lines[:i])
                try:
                    import ast
                    fn_tree = ast.parse(candidate)
                    for node in ast.walk(fn_tree):
                        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            fn_lines = candidate.splitlines(keepends=True)
                            isolated_function = "".join(fn_lines[node.lineno - 1:node.end_lineno])
                            break
                    if isolated_function:
                        break
                except Exception:
                    continue

            if isolated_function:
                orig_lines = original_content.splitlines(keepends=True)
                new_full_content = (
                    "".join(orig_lines[:target_node.lineno - 1])
                    + isolated_function.rstrip() + "\n"
                    + "".join(orig_lines[target_node.end_lineno:])
                )
            else:
                new_full_content = original_content
        else:
            # Full file repair
            prompt = f"""You are a master Python software engineer.
Rewrite the complete code for this file with the bug fixed so all unit tests pass.
Output ONLY the raw Python code. Do NOT output markdown code fences or conversational text.

FILE: {rel_target}
ERROR: {classification.error_message}
RCA: {rca.root_cause_summary}
STRATEGY: {rca.fix_strategy}

ORIGINAL CODE:
{original_content}

CORRECTED CODE:"""

            raw_fixed = ollama_client.generate(
                prompt=prompt,
                model=settings.LLM_CODE_MODEL,
                temperature=0.1,
                num_predict=400
            )
            clean_fixed = raw_fixed.strip()
            if "```" in clean_fixed:
                clean_fixed = re.sub(r"```(?:python)?\s*\n?", "", clean_fixed)
                clean_fixed = re.sub(r"\n?```$", "", clean_fixed).strip()
            new_full_content = clean_fixed

        # Compute unified diff
        orig_lines = original_content.splitlines(keepends=True)
        fixed_lines = [l + "\n" if not l.endswith("\n") else l for l in new_full_content.splitlines(keepends=True)]

        diff = list(difflib.unified_diff(
            orig_lines,
            fixed_lines,
            fromfile=f"a/{rel_target}",
            tofile=f"b/{rel_target}",
            n=3
        ))
        unified_diff_str = "".join(diff)

        # Count changed lines
        added_count = sum(1 for line in diff if line.startswith("+") and not line.startswith("+++"))
        deleted_count = sum(1 for line in diff if line.startswith("-") and not line.startswith("---"))
        lines_changed = added_count + deleted_count

        return FixProposal(
            target_file=rel_target,
            original_snippet=original_content,
            replacement_snippet=new_full_content,
            unified_diff=unified_diff_str,
            lines_changed=lines_changed
        )

fix_generator = FixGenerator()
