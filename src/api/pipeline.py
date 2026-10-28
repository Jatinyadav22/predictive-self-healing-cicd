import time
from datetime import datetime
from typing import Optional, Any
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from src.services.coordinator import coordinator
from src.services.audit_service import audit_logger
from demo_repo.bug_scenarios import inject_fault, reset_demo_repo, SCENARIOS

router = APIRouter(prefix="/api/pipelines", tags=["Pipelines"])

latest_webhook_event = {
    "status": "WAITING",
    "received_at": None,
    "commit_sha": None,
    "commit_message": None,
    "author": None,
    "branch": None,
    "repository": None,
    "run_url": None,
    "run_id": None,
    "pipeline_status": None,
    "pipeline_run_id": None,
    "healed_content": None,
    "unified_diff": None,
    "rca_summary": None,
    "risk_score": None
}

class TriggerPipelineRequest(BaseModel):
    commit_sha: Optional[str] = None
    branch: str = "main"
    author: str = "developer"
    lines_added: int = 45
    lines_deleted: int = 10
    files_changed: int = 2
    test_lines_added: int = 20
    config_files_touched: int = 0
    ci_files_touched: int = 0
    author_recent_failure_rate: float = 0.10
    scenario: Optional[str] = None

class InjectBugRequest(BaseModel):
    scenario: str

@router.post("/trigger")
def trigger_pipeline(payload: TriggerPipelineRequest):
    run = coordinator.execute_pipeline(
        commit_sha=payload.commit_sha or "HEAD",
        branch=payload.branch,
        author=payload.author,
        lines_added=payload.lines_added,
        lines_deleted=payload.lines_deleted,
        files_changed=payload.files_changed,
        test_lines_added=payload.test_lines_added,
        config_files_touched=payload.config_files_touched,
        ci_files_touched=payload.ci_files_touched,
        author_recent_failure_rate=payload.author_recent_failure_rate,
        scenario=payload.scenario
    )
    return run

@router.get("/runs")
def list_runs(limit: int = 25):
    return audit_logger.list_pipeline_runs(limit=limit)

@router.get("/runs/{run_id}")
def get_run(run_id: str):
    run = audit_logger.get_pipeline_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Pipeline run not found")
    return run

@router.post("/runs/{run_id}/approve")
def approve_run(run_id: str):
    success = coordinator.apply_approved_fix(run_id)
    if not success:
        raise HTTPException(status_code=400, detail="Could not apply approved fix. Verify run status.")
    return {"status": "approved", "run_id": run_id}

@router.post("/runs/{run_id}/reject")
def reject_run(run_id: str):
    from src.models.schemas import PipelineStatus
    run = audit_logger.get_pipeline_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    run.status = PipelineStatus.FAILED
    audit_logger.save_pipeline_run(run)
    audit_logger.record_event(
        event_type="HUMAN_APPROVAL_REJECTED",
        summary=f"Run {run_id} fix rejected by human operator.",
        run_id=run_id,
        actor="HUMAN_OPERATOR"
    )
    return {"status": "rejected", "run_id": run_id}

@router.post("/inject-fault")
def inject_fault_api(payload: InjectBugRequest):
    scenario_id = payload.scenario
    if scenario_id not in SCENARIOS:
        raise HTTPException(status_code=400, detail=f"Unknown scenario ID: {scenario_id}")
    msg = inject_fault(scenario_id)
    return {"status": "injected", "scenario": scenario_id, "message": msg}

@router.post("/reset-repo")
def reset_repo_api():
    reset_demo_repo()
    return {"status": "reset", "message": "Demo repository reset to clean state."}

@router.get("/scenarios")
def get_scenarios():
    return SCENARIOS

@router.post("/webhook/github")
async def github_webhook_endpoint(request: Request):
    """Receives failure webhook from GitHub Actions, triggers autonomous RAG RCA + AST repair."""
    global latest_webhook_event
    try:
        body = await request.json()
    except Exception:
        body = {}

    commit_sha = body.get("commit_sha") or body.get("after") or body.get("head_commit", {}).get("id") or "HEAD"
    if len(commit_sha) > 40:
        commit_sha = commit_sha[:40]

    commit_msg = body.get("commit_message") or body.get("head_commit", {}).get("message") or "GitHub Actions Failure"
    branch = body.get("branch") or body.get("ref", "refs/heads/main").replace("refs/heads/", "")
    author = body.get("author") or body.get("head_commit", {}).get("author", {}).get("username") or body.get("sender", {}).get("login") or "github-actions"
    repo = body.get("repository")
    if isinstance(repo, dict):
        repo_name = repo.get("full_name", "Jatinyadav22/predictive-self-healing-cicd")
    else:
        repo_name = str(repo) if repo else "Jatinyadav22/predictive-self-healing-cicd"

    run_id_val = str(body.get("run_id") or body.get("workflow_run", {}).get("id") or int(time.time()))
    run_url = body.get("run_url") or (f"https://github.com/{repo_name}/actions/runs/{run_id_val}" if run_id_val else None)
    failure_logs = body.get("failure_logs") or ""
    demo_app_content = body.get("demo_app_content")

    latest_webhook_event = {
        "status": "PROCESSING",
        "received_at": datetime.utcnow().isoformat(),
        "commit_sha": commit_sha[:8] if commit_sha else "HEAD",
        "full_sha": commit_sha,
        "commit_message": commit_msg[:120] if commit_msg else "",
        "author": author,
        "branch": branch,
        "repository": repo_name,
        "run_url": run_url,
        "run_id": run_id_val,
        "pipeline_status": "ANALYZING",
        "pipeline_run_id": None,
        "healed_content": None,
        "unified_diff": None,
        "rca_summary": None,
        "risk_score": None
    }

    run = coordinator.execute_pipeline(
        commit_sha=commit_sha[:8] if commit_sha else "HEAD",
        branch=branch,
        author=author,
        lines_added=int(body.get("lines_added", 20)),
        lines_deleted=int(body.get("lines_deleted", 5)),
        files_changed=int(body.get("files_changed", 1)),
        test_lines_added=int(body.get("test_lines_added", 0)),
        config_files_touched=int(body.get("config_files_touched", 0)),
        ci_files_touched=int(body.get("ci_files_touched", 0)),
        author_recent_failure_rate=float(body.get("author_recent_failure_rate", 0.15)),
        trigger_source="GITHUB_ACTIONS_WEBHOOK",
        commit_message=commit_msg,
        run_url=run_url,
        repository=repo_name,
        incoming_file_content=demo_app_content,
        raw_failure_logs=failure_logs
    )

    healed_code = None
    unified_diff = None
    rca_text = ""
    target_file = "demo_repo/app.py"

    if run.healing_attempts and run.healing_attempts[-1].fix_proposal:
        fix = run.healing_attempts[-1].fix_proposal
        healed_code = fix.replacement_snippet
        unified_diff = fix.unified_diff
        target_file = fix.target_file
        if run.healing_attempts[-1].rca:
            rca_text = run.healing_attempts[-1].rca.root_cause_summary

    latest_webhook_event["status"] = "COMPLETED"
    latest_webhook_event["pipeline_status"] = run.status.value
    latest_webhook_event["healed_content"] = healed_code
    latest_webhook_event["unified_diff"] = unified_diff
    latest_webhook_event["rca_summary"] = rca_text
    latest_webhook_event["pipeline_run_id"] = run.run_id
    latest_webhook_event["risk_score"] = run.risk_prediction.risk_score if run.risk_prediction else 0.0

    return {
        "status": run.status.value,
        "run_id": run.run_id,
        "commit_sha": commit_sha,
        "branch": branch,
        "repository": repo_name,
        "target_file": target_file,
        "healed_content": healed_code,
        "unified_diff": unified_diff,
        "rca_summary": rca_text,
        "risk_score": run.risk_prediction.risk_score if run.risk_prediction else 0.0,
        "risk_tier": run.risk_prediction.risk_tier.value if run.risk_prediction else "LOW",
        "message": "AutoHeal webhook handled successfully."
    }

@router.get("/latest-webhook")
def get_latest_webhook():
    return latest_webhook_event
