import math
from typing import Any

class CommitFeatureExtractor:
    """Extracts 12 quantitative software metrics from commits for ML risk prediction."""

    @staticmethod
    def extract_features(
        lines_added: int = 25,
        lines_deleted: int = 5,
        files_changed: int = 2,
        test_lines_added: int = 15,
        config_files_touched: int = 0,
        ci_files_touched: int = 0,
        is_weekend: int = 0,
        hour_of_day: int = 14,
        author_experience_commits: int = 60,
        author_recent_failure_rate: float = 0.08
    ) -> dict[str, float]:
        total_churn = float(lines_added + lines_deleted)
        test_ratio = float(test_lines_added) / (float(lines_added) + 1.0)
        entropy = 0.5 if files_changed <= 1 else min(1.0, math.log2(files_changed) / 3.0)

        return {
            "lines_added": float(lines_added),
            "lines_deleted": float(lines_deleted),
            "files_changed": float(files_changed),
            "total_churn": total_churn,
            "test_lines_ratio": round(test_ratio, 3),
            "config_files_touched": float(config_files_touched),
            "ci_files_touched": float(ci_files_touched),
            "is_weekend": float(is_weekend),
            "hour_of_day": float(hour_of_day),
            "author_experience_commits": float(author_experience_commits),
            "author_recent_failure_rate": float(author_recent_failure_rate),
            "code_entropy": round(entropy, 3)
        }

    @staticmethod
    def explain_prediction(features: dict[str, float], risk_score: float) -> list[str]:
        explanations = []
        churn = features.get("total_churn", 0.0)
        test_ratio = features.get("test_lines_ratio", 0.0)
        config_touch = features.get("config_files_touched", 0.0)
        ci_touch = features.get("ci_files_touched", 0.0)
        hour = features.get("hour_of_day", 12.0)
        fail_rate = features.get("author_recent_failure_rate", 0.0)

        if churn > 200:
            explanations.append(f"High Code Churn: Large commit with {int(churn)} total lines altered across {int(features.get('files_changed', 1))} files.")
        elif churn > 50:
            explanations.append(f"Moderate Code Churn: {int(churn)} lines altered across {int(features.get('files_changed', 1))} files.")
        else:
            explanations.append(f"Minimal Code Churn: Safe small delta of {int(churn)} lines.")

        if test_ratio < 0.1 and churn > 30:
            explanations.append("Insufficient Test Coverage: Substantial production code changes with negligible corresponding unit test updates.")
        elif test_ratio >= 0.3:
            explanations.append("Proportional Test Updates: Commit includes relevant test suite updates, decreasing failure risk.")

        if ci_touch > 0 or config_touch > 0:
            explanations.append("Pipeline/Infrastructure Modification: Changes to CI workflow definitions or critical service config files.")

        if hour < 6 or hour > 21:
            explanations.append("Off-Hours Commit: Push outside normal core development hours, statistically correlated with higher regression rates.")

        if fail_rate > 0.25:
            explanations.append(f"Elevated Historical Failure Frequency: Author's recent CI failure rate is {int(fail_rate * 100)}%.")

        return explanations

feature_extractor = CommitFeatureExtractor()
