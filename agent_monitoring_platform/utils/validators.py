from typing import Any, Dict, List, Optional, Tuple


def validate_metric(metric_name: str, value: float, tags: Optional[Dict[str, str]] = None) -> Tuple[bool, Optional[str]]:
    """Validate a metric"""

    if not metric_name:
        return False, "Metric name is required"

    if not isinstance(metric_name, str):
        return False, "Metric name must be a string"

    if not isinstance(value, (int, float)):
        return False, "Metric value must be a number"

    if tags and not isinstance(tags, dict):
        return False, "Metric tags must be a dictionary"

    return True, None


def validate_evaluation_result(
    evaluator_name: str, test_case_id: str, score: float, error: Optional[str] = None
) -> Tuple[bool, Optional[str]]:
    """Validate an evaluation result"""

    if not evaluator_name:
        return False, "Evaluator name is required"

    if not test_case_id:
        return False, "Test case ID is required"

    if not isinstance(score, (int, float)):
        return False, "Score must be a number"

    if not (0 <= score <= 1):
        return False, "Score must be between 0 and 1"

    return True, None


def validate_agent_execution(
    agent_id: str, duration_ms: float, tokens_used: int, success: bool
) -> Tuple[bool, Optional[str]]:
    """Validate agent execution data"""

    if not agent_id:
        return False, "Agent ID is required"

    if not isinstance(duration_ms, (int, float)):
        return False, "Duration must be a number"

    if duration_ms < 0:
        return False, "Duration must be non-negative"

    if not isinstance(tokens_used, int):
        return False, "Tokens used must be an integer"

    if tokens_used < 0:
        return False, "Tokens used must be non-negative"

    if not isinstance(success, bool):
        return False, "Success must be a boolean"

    return True, None


def validate_alert_rule(rule_id: str, metric_name: str, threshold: float, severity: str) -> Tuple[bool, Optional[str]]:
    """Validate an alert rule"""

    if not rule_id:
        return False, "Rule ID is required"

    if not metric_name:
        return False, "Metric name is required"

    if not isinstance(threshold, (int, float)):
        return False, "Threshold must be a number"

    valid_severities = ["info", "warning", "error", "critical"]
    if severity not in valid_severities:
        return False, f"Severity must be one of {valid_severities}"

    return True, None
