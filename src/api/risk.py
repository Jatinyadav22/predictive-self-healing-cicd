from fastapi import APIRouter
from pydantic import BaseModel
from src.services.feature_extractor import feature_extractor
from src.services.risk_engine import risk_engine

router = APIRouter(prefix="/api/risk", tags=["Risk"])

class RiskEvaluationRequest(BaseModel):
    lines_added: int = 50
    lines_deleted: int = 10
    files_changed: int = 2
    test_lines_added: int = 15
    config_files_touched: int = 0
    ci_files_touched: int = 0
    is_weekend: int = 0
    hour_of_day: int = 14
    author_experience_commits: int = 60
    author_recent_failure_rate: float = 0.10

@router.post("/evaluate")
def evaluate_risk(payload: RiskEvaluationRequest):
    features = feature_extractor.extract_features(
        lines_added=payload.lines_added,
        lines_deleted=payload.lines_deleted,
        files_changed=payload.files_changed,
        test_lines_added=payload.test_lines_added,
        config_files_touched=payload.config_files_touched,
        ci_files_touched=payload.ci_files_touched,
        is_weekend=payload.is_weekend,
        hour_of_day=payload.hour_of_day,
        author_experience_commits=payload.author_experience_commits,
        author_recent_failure_rate=payload.author_recent_failure_rate
    )
    prediction = risk_engine.predict(features)
    return prediction

@router.get("/evaluation")
def get_risk_model_evaluation():
    """Returns held-out evaluation metrics, baseline comparison, and limitations of the risk predictor."""
    return risk_engine.get_evaluation_metrics()

