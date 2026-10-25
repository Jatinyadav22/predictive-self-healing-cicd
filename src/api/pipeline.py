from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from src.services.coordinator import coordinator
from src.services.audit_service import audit_logger
from demo_repo.bug_scenarios import inject_fault, reset_demo_repo, SCENARIOS

router = APIRouter(prefix="/api/pipelines", tags=["Pipelines"])

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
