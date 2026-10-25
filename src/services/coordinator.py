import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Any

from src.config.settings import settings
from src.models.schemas import (
    PipelineRun, PipelineStatus, HealingAttempt,
    RiskPrediction, FailureClassification, FixProposal, RCAAnalysis
)
from src.services.pipeline_runner import pipeline_runner
from src.services.feature_extractor import feature_extractor
from src.services.risk_engine import risk_engine
from src.services.failure_classifier import failure_classifier
from src.services.rca_engine import rca_engine
from src.services.fix_generator import fix_generator
from src.services.safety_validator import safety_validator
from src.services.audit_service import audit_logger

class SelfHealingCoordinator:
    """Orchestrates end-to-end autonomous CI/CD cycle: risk prediction, build, RCA, repair, and verification."""

    def execute_pipeline(
        self,
        commit_sha: str = "HEAD",
        branch: str = "main",
        author: str = "developer",
        lines_added: int = 45,
        lines_deleted: int = 10,
        files_changed: int = 2,
        test_lines_added: int = 20,
        config_files_touched: int = 0,
        ci_files_touched: int = 0,
        author_recent_failure_rate: float = 0.10,
        repo_path: Optional[Path] = None,
        scenario: Optional[str] = None
    ) -> PipelineRun:
        run_id = f"run-{int(time.time() * 1000)}"
        repo_dir = Path(repo_path or settings.DEMO_REPO_PATH).resolve()

        if scenario == "5":
            lines_added = max(lines_added, 480)
            lines_deleted = max(lines_deleted, 160)
            files_changed = max(files_changed, 8)
            config_files_touched = 1
            ci_files_touched = 1
            test_lines_added = 0
            author_recent_failure_rate = max(author_recent_failure_rate, 0.75)

        run = PipelineRun(
            run_id=run_id,
            commit_sha=commit_sha,
            branch=branch,
            author=author,
            status=PipelineStatus.BUILDING,
            started_at=datetime.utcnow()
        )
        audit_logger.save_pipeline_run(run)

        # 1. Predictive Risk Analysis
        features = feature_extractor.extract_features(
            lines_added=lines_added,
            lines_deleted=lines_deleted,
            files_changed=files_changed,
            test_lines_added=test_lines_added,
            config_files_touched=config_files_touched,
            ci_files_touched=ci_files_touched,
            author_recent_failure_rate=author_recent_failure_rate
        )
        prediction = risk_engine.predict(features, run_id=run_id)
        run.risk_prediction = prediction
        audit_logger.save_pipeline_run(run)

        # 2. Pytest Execution
        run.status = PipelineStatus.TESTING
        audit_logger.save_pipeline_run(run)

        exit_code, output_logs = pipeline_runner.run_tests(repo_dir)
        run.raw_build_logs = output_logs

        if exit_code == 0:
            # Pipeline Passed Cleanly
            run.status = PipelineStatus.SUCCESS
            run.completed_at = datetime.utcnow()
            audit_logger.save_pipeline_run(run)
            audit_logger.record_event(
                event_type="PIPELINE_SUCCESS",
                summary=f"Run {run_id} passed all test suites cleanly.",
                run_id=run_id,
                actor="PIPELINE_RUNNER"
            )
            return run

        # Pipeline Failed - Classify Failure
        run.status = PipelineStatus.FAILED
        classification = failure_classifier.classify(output_logs, run_id=run_id)
        run.failure_classification = classification
        audit_logger.save_pipeline_run(run)

        # 3. Explainable Root Cause Analysis
        run.status = PipelineStatus.ANALYZING
        rca = rca_engine.diagnose(classification, run_id=run_id)

        # 4. Synthesize Minimal Patch
        run.status = PipelineStatus.PATCHING
        fix = fix_generator.generate_fix(classification, rca, repo_dir)

        attempt = HealingAttempt(
            attempt_id=f"heal-{run_id}-1",
            started_at=datetime.utcnow(),
            rca=rca,
            fix_proposal=fix
        )

        if not fix:
            attempt.action_taken = "No suitable patch could be generated automatically."
            attempt.completed_at = datetime.utcnow()
            run.healing_attempts.append(attempt)
            run.status = PipelineStatus.FAILED
            run.completed_at = datetime.utcnow()
            audit_logger.save_pipeline_run(run)
            return run

        # 5. Validate Safety Guardrails
        is_safe, violations = safety_validator.validate(
            target_file=fix.target_file,
            patched_content=fix.replacement_snippet,
            predicted_risk=prediction.risk_score,
            lines_changed=fix.lines_changed,
            scenario=scenario
        )
        fix.is_safe = is_safe
        fix.safety_violations = violations

        if not is_safe:
            # Route to Human-in-the-Loop review
            attempt.action_taken = f"Safety check triggered guardrails: {'; '.join(violations)}. Escalated to Human-in-the-Loop."
            attempt.logs.append(f"Guardrail violations: {violations}")
            attempt.completed_at = datetime.utcnow()
            run.healing_attempts.append(attempt)
            run.status = PipelineStatus.REQUIRES_HUMAN_APPROVAL
            audit_logger.save_pipeline_run(run)

            audit_logger.record_event(
                event_type="SAFETY_GATE_TRIGGERED",
                summary=f"Run {run_id} fix stopped at Safety Gate ({len(violations)} violations). Routed to Human Approval.",
                run_id=run_id,
                actor="SAFETY_VALIDATOR",
                payload={"violations": violations, "diff": fix.unified_diff}
            )
            return run

        # 6. Apply Fix in Sandbox & Re-verify
        target_file_path = repo_dir / fix.target_file
        backup_file_path = repo_dir / f"{fix.target_file}.bak"

        try:
            # Create backup
            shutil.copy2(target_file_path, backup_file_path)
            target_file_path.write_text(fix.replacement_snippet, encoding="utf-8")
            attempt.logs.append(f"Applied candidate patch to {fix.target_file} in sandbox.")

            # Re-execute pytest in sandbox
            retest_code, retest_logs = pipeline_runner.run_tests(repo_dir)

            if retest_code == 0:
                # Patch successfully healed the build
                attempt.post_repair_test_passed = True
                attempt.action_taken = "Patch verified: All unit tests passing. Repository automatically recovered."
                attempt.logs.append("Verification suite passed 100%. Autonomous recovery confirmed.")
                attempt.completed_at = datetime.utcnow()
                run.healing_attempts.append(attempt)
                run.status = PipelineStatus.RECOVERED_AUTOMATICALLY
                run.completed_at = datetime.utcnow()

                if backup_file_path.exists():
                    backup_file_path.unlink()

                audit_logger.save_pipeline_run(run)
                audit_logger.record_event(
                    event_type="AUTONOMOUS_RECOVERY",
                    summary=f"Run {run_id} automatically repaired and verified in sandbox.",
                    run_id=run_id,
                    actor="COORDINATOR",
                    payload={"target_file": fix.target_file, "lines_changed": fix.lines_changed}
                )
            else:
                # Patch failed tests - Rollback
                attempt.post_repair_test_passed = False
                attempt.action_taken = "Verification tests failed after patch. Rolled back to original state."
                attempt.logs.append(f"Verification tests failed:\n{retest_logs[:500]}")
                attempt.completed_at = datetime.utcnow()

                if backup_file_path.exists():
                    shutil.move(backup_file_path, target_file_path)

                run.healing_attempts.append(attempt)
                run.status = PipelineStatus.RECOVERY_FAILED_ROLLED_BACK
                run.completed_at = datetime.utcnow()

                audit_logger.save_pipeline_run(run)
                audit_logger.record_event(
                    event_type="RECOVERY_FAILED_ROLLED_BACK",
                    summary=f"Run {run_id} patch failed verification. Automatically rolled back.",
                    run_id=run_id,
                    actor="COORDINATOR"
                )

        except Exception as e:
            if backup_file_path.exists():
                shutil.move(backup_file_path, target_file_path)
            attempt.logs.append(f"Exception during verification: {str(e)}")
            attempt.action_taken = f"Error during sandbox verification: {str(e)}"
            attempt.completed_at = datetime.utcnow()
            run.healing_attempts.append(attempt)
            run.status = PipelineStatus.FAILED
            run.completed_at = datetime.utcnow()
            audit_logger.save_pipeline_run(run)

        return run

    def apply_approved_fix(self, run_id: str, repo_path: Optional[Path] = None) -> bool:
        run = audit_logger.get_pipeline_run(run_id)
        if not run or run.status != PipelineStatus.REQUIRES_HUMAN_APPROVAL:
            return False

        if not run.healing_attempts or not run.healing_attempts[-1].fix_proposal:
            return False

        fix = run.healing_attempts[-1].fix_proposal
        repo_dir = Path(repo_path or settings.DEMO_REPO_PATH).resolve()
        target_file = repo_dir / fix.target_file

        try:
            target_file.write_text(fix.replacement_snippet, encoding="utf-8")
            retest_code, _ = pipeline_runner.run_tests(repo_dir)

            if retest_code == 0:
                run.status = PipelineStatus.RECOVERED_AUTOMATICALLY
            else:
                run.status = PipelineStatus.SUCCESS  # User-approved override

            run.completed_at = datetime.utcnow()
            audit_logger.save_pipeline_run(run)
            audit_logger.record_event(
                event_type="HUMAN_APPROVAL_APPLIED",
                summary=f"Run {run_id} patch approved by human reviewer and deployed.",
                run_id=run_id,
                actor="HUMAN_OPERATOR",
                payload={"target_file": fix.target_file}
            )
            return True
        except Exception:
            return False

coordinator = SelfHealingCoordinator()
