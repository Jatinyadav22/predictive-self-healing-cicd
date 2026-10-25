from typing import Optional
from src.models.schemas import FailureClassification, FailureType
from src.services.log_parser import log_parser, ParsedError
from src.services.audit_service import audit_logger

class FailureClassifier:
    """Classifies software and pipeline failures into standardized failure types."""

    @staticmethod
    def classify(raw_log: str, run_id: Optional[str] = None) -> FailureClassification:
        parsed: Optional[ParsedError] = log_parser.parse_pytest_log(raw_log)

        if not parsed:
            classification = FailureClassification(
                failure_type=FailureType.UNKNOWN,
                error_message="Could not parse error from logs",
                stack_trace=raw_log[:1000]
            )
            return classification

        err_type_str = (parsed.error_type or "").lower()
        err_msg_str = (parsed.error_message or "").lower()
        trace_str = (parsed.stack_trace_snippet or "").lower()

        # Rule-based classification
        if any(w in err_type_str for w in ["syntaxerror", "indentationerror", "taberror"]) or "syntaxerror" in trace_str:
            failure_type = FailureType.SYNTAX_ERROR
        elif any(w in err_type_str for w in ["modulenotfounderror", "importerror"]) or "no module named" in err_msg_str:
            failure_type = FailureType.IMPORT_DEPENDENCY_ERROR
        elif any(w in err_type_str for w in ["assertionerror", "assert"]) or "assert " in trace_str or "assertion" in trace_str:
            failure_type = FailureType.LOGIC_ASSERTION_FAILURE
        elif any(w in err_type_str for w in ["keyerror", "filenotfounderror", "scannererror"]) and any(c in trace_str for c in [".yml", ".yaml", "config", "settings"]):
            failure_type = FailureType.CONFIG_WORKFLOW_TYPO
        elif any(w in err_type_str for w in ["permissionerror", "connectionrefusederror", "oserror"]):
            failure_type = FailureType.ENVIRONMENT_MISMATCH
        elif any(w in err_type_str for w in ["timeouterror", "deadlineexceeded"]) or "timed out" in err_msg_str:
            failure_type = FailureType.TIMEOUT
        elif "assertionerror" in err_type_str or "assert" in err_msg_str:
            failure_type = FailureType.LOGIC_ASSERTION_FAILURE
        else:
            failure_type = FailureType.UNKNOWN

        classification = FailureClassification(
            failure_type=failure_type,
            failing_file=parsed.failing_file,
            failing_line=parsed.failing_line,
            failing_symbol=parsed.failing_symbol,
            failing_test_name=parsed.failing_test_name,
            error_message=f"{parsed.error_type}: {parsed.error_message}",
            stack_trace=parsed.stack_trace_snippet
        )

        if run_id:
            audit_logger.record_event(
                event_type="DETECT_FAILURE",
                summary=f"Run {run_id} failed with {failure_type.value}: {classification.error_message[:80]}",
                run_id=run_id,
                actor="FAILURE_CLASSIFIER",
                payload=classification.model_dump(mode="json")
            )

        return classification

failure_classifier = FailureClassifier()
