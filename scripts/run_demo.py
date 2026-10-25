import argparse
import sys
import time
from pathlib import Path
from src.services.coordinator import coordinator
from demo_repo.bug_scenarios import inject_fault, reset_demo_repo, SCENARIOS

def print_header(title: str):
    print("\n" + "═" * 70)
    print(f"🚀 {title}")
    print("═" * 70 + "\n")

def run_demo(scenario_id: str):
    print_header("AUTONOMOUS CI/CD PIPELINE EXECUTION")

    if scenario_id == "clean":
        print("👉 Running Clean Baseline Commit (No Fault Injected)...")
        reset_demo_repo()
        lines_added = 30
        lines_deleted = 5
        author_fail = 0.05
    elif scenario_id in SCENARIOS:
        s = SCENARIOS[scenario_id]
        print(f"👉 Injecting Fault: {s['name']}")
        print(f"   Target: {s['target_file']} | {s['description']}\n")
        inject_fault(scenario_id)

        if scenario_id == "5":
            lines_added = 270
            lines_deleted = 30
            author_fail = 0.35
        else:
            lines_added = 55
            lines_deleted = 12
            author_fail = 0.08
    else:
        print(f"❌ Unknown scenario: {scenario_id}")
        sys.exit(1)

    print("1. 🎯 Running Predictive ML Risk Engine (Pre-execution check)...")
    run = coordinator.execute_pipeline(
        commit_sha=f"sha-{int(time.time())}"[-8:],
        branch="main",
        author="devops-engineer",
        lines_added=lines_added,
        lines_deleted=lines_deleted,
        files_changed=2,
        test_lines_added=20,
        author_recent_failure_rate=author_fail
    )

    if run.risk_prediction:
        print(f"   ► Predicted Risk: {run.risk_prediction.risk_score}% ({run.risk_prediction.risk_tier.value} RISK)")
        for factor in run.risk_prediction.top_risk_factors:
            print(f"     • {factor}")

    print("\n2. 🧪 Executing Pipeline Test Suite (pytest in demo_repo)...")
    if run.status == "SUCCESS":
        print("   ✅ ALL UNIT TESTS PASSED CLEANLY!")
        print(f"\nFinal Pipeline Status: {run.status.value}")
        return

    print("   ✕ PIPELINE FAILED! Isolate and classify failure...")
    if run.failure_classification:
        fc = run.failure_classification
        print(f"   ► Failure Classification: {fc.failure_type.value}")
        print(f"   ► Offending Location:     {fc.failing_file or 'unknown'}:{fc.failing_line or '?'}")
        print(f"   ► Error Message:          {fc.error_message[:100]}")

    print("\n3. 🧠 Triggering Explainable Self-Healing Agent...")
    if run.healing_attempts:
        attempt = run.healing_attempts[-1]
        if attempt.rca:
            print(f"   ► Root Cause: {attempt.rca.root_cause_summary}")
            print(f"   ► Confidence: {int(attempt.rca.confidence_score * 100)}%")
            print(f"   ► Strategy:   {attempt.rca.fix_strategy}")
            print(f"   ► Evidence:   {len(attempt.rca.evidence_citations)} context citations from ChromaDB")

        if attempt.fix_proposal:
            fix = attempt.fix_proposal
            safety_str = "PASSED" if fix.is_safe else "GUARDRAIL TRIGGERED (HITL)"
            print(f"\n4. 🩹 Candidate Patch Generated for {fix.target_file}:")
            print(f"   ► Lines Changed: {fix.lines_changed} | Safety Check: {safety_str}")
            print("\n" + fix.unified_diff)

    print(f"\nFinal Pipeline Status: {run.status.value}")
    if run.status == "RECOVERED_AUTOMATICALLY":
        print("✨ SUCCESS: The autonomous agent repaired and re-verified the pipeline in sandbox!\n")
    elif run.status == "REQUIRES_HUMAN_APPROVAL":
        print("⚠️ PENDING: High-risk change stopped at Safety Gate. Open Web Dashboard to Approve/Reject.\n")
    elif run.status == "RECOVERY_FAILED_ROLLED_BACK":
        print("🛡️ ROLLED BACK: Sandbox tests failed after patch. Original codebase safely restored.\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Autonomous CI/CD Self-Healing Demo")
    parser.add_argument("--scenario", default="1", help="Scenario ID (1-5 or 'clean')")
    args = parser.parse_args()
    run_demo(args.scenario)
