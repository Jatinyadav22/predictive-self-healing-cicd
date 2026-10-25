import pytest
from fastapi.testclient import TestClient
from src.main import app
from src.services.feature_extractor import feature_extractor
from src.services.risk_engine import risk_engine
from src.services.failure_classifier import failure_classifier
from src.services.safety_validator import safety_validator
from src.services.audit_service import audit_logger
from src.models.schemas import FailureType, RiskTier

client = TestClient(app)

def test_feature_extractor():
    features = feature_extractor.extract_features(
        lines_added=100,
        lines_deleted=20,
        files_changed=3,
        test_lines_added=40,
        author_recent_failure_rate=0.05
    )
    assert features["total_churn"] == 120.0
    assert features["files_changed"] == 3.0
    assert features["test_lines_ratio"] > 0.3

    explanations = feature_extractor.explain_prediction(features, 15.0)
    assert any("Code Churn" in exp for exp in explanations)
    assert any("Test Updates" in exp for exp in explanations)

def test_risk_engine_prediction():
    features = feature_extractor.extract_features(
        lines_added=20,
        lines_deleted=5,
        files_changed=1,
        test_lines_added=15,
        author_recent_failure_rate=0.02
    )
    pred = risk_engine.predict(features)
    assert 0.0 <= pred.risk_score <= 100.0
    assert pred.risk_tier in [RiskTier.LOW, RiskTier.MEDIUM, RiskTier.HIGH, RiskTier.CRITICAL]
    assert len(pred.top_risk_factors) > 0

def test_failure_classifier_syntax_error():
    log = """
    File "app.py", line 42
        def calculate_tax(amount: float, state: str = "DEFAULT") -> float
                                                                         ^
    SyntaxError: expected ':'
    """
    classification = failure_classifier.classify(log)
    assert classification.failure_type == FailureType.SYNTAX_ERROR
    assert classification.failing_file == "app.py"

def test_failure_classifier_assertion_failure():
    log = """
    ____________________ test_apply_discount_standard ____________________
    def test_apply_discount_standard():
    >       assert apply_discount(100.0, 10.0) == 90.0
    E       AssertionError: assert 85.0 == 90.0
    tests/test_app.py:18: AssertionError
    """
    classification = failure_classifier.classify(log)
    assert classification.failure_type == FailureType.LOGIC_ASSERTION_FAILURE
    assert "85.0 == 90.0" in classification.error_message

def test_safety_validator_pass():
    valid_code = "def add(a, b):\n    return a + b\n"
    is_safe, violations = safety_validator.validate("calculator.py", valid_code, predicted_risk=15.0, lines_changed=3)
    assert is_safe is True
    assert len(violations) == 0

def test_safety_validator_syntax_error():
    broken_code = "def add(a, b\n    return a + b\n"
    is_safe, violations = safety_validator.validate("calculator.py", broken_code, predicted_risk=15.0, lines_changed=3)
    assert is_safe is False
    assert any("Syntax validation failed" in v for v in violations)

def test_safety_validator_sensitive_file():
    code = "API_KEY = 'secret'\n"
    is_safe, violations = safety_validator.validate(".env", code, predicted_risk=10.0, lines_changed=2)
    assert is_safe is False
    assert any("sensitive" in v.lower() for v in violations)

def test_safety_validator_risk_ceiling():
    valid_code = "x = 1\n"
    is_safe, violations = safety_validator.validate("app.py", valid_code, predicted_risk=75.0, lines_changed=2)
    assert is_safe is False
    assert any("risk score" in v.lower() for v in violations)

def test_audit_logger_hash_chaining():
    event1 = audit_logger.record_event(
        event_type="TEST_EVENT_A",
        summary="First test audit record",
        actor="UNIT_TEST"
    )
    event2 = audit_logger.record_event(
        event_type="TEST_EVENT_B",
        summary="Second test audit record",
        actor="UNIT_TEST"
    )
    assert event1.event_hash != ""
    assert event2.event_hash != ""
    assert event2.previous_event_hash == event1.event_hash


def test_risk_evaluation_endpoint():
    response = client.post(
        "/api/risk/evaluate",
        json={
            "lines_added": 20,
            "lines_deleted": 5,
            "files_changed": 1,
            "test_lines_added": 10,
            "author_recent_failure_rate": 0.05
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "risk_score" in data
    assert "risk_tier" in data
    assert "top_risk_factors" in data


def test_risk_model_evaluation_metrics_and_baseline():
    response = client.get("/api/risk/evaluation")
    assert response.status_code == 200
    data = response.json()
    assert data["dataset"] == "DEMONSTRATION_SYNTHETIC_CI_DATASET"
    assert "model_metrics" in data
    assert "baseline_metrics" in data
    assert "confusion_matrix" in data
    assert "limitations" in data
    assert data["model_metrics"]["accuracy"] >= data["baseline_metrics"]["accuracy"]

