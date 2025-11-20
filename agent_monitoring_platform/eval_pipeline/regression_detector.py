from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class RegressionType(str, Enum):
    SIGNIFICANT_DROP = "significant_drop"
    MINOR_DROP = "minor_drop"
    NO_REGRESSION = "no_regression"
    IMPROVEMENT = "improvement"


@dataclass
class RegressionAlert:
    metric_name: str
    regression_type: RegressionType
    current_value: float
    baseline_value: float
    change_percent: float
    p_value: Optional[float] = None
    severity: str = "info"


@dataclass
class RegressionReport:
    metric_name: str
    baseline_mean: float
    baseline_std: float
    current_mean: float
    current_std: float
    change_percent: float
    regression_detected: bool
    alerts: List[RegressionAlert] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metric_name": self.metric_name,
            "baseline_mean": self.baseline_mean,
            "baseline_std": self.baseline_std,
            "current_mean": self.current_mean,
            "current_std": self.current_std,
            "change_percent": self.change_percent,
            "regression_detected": self.regression_detected,
            "alerts": [{"type": a.regression_type.value, "severity": a.severity} for a in self.alerts],
        }


class RegressionDetector:
    def __init__(self, significance_threshold: float = 0.05, percent_threshold: float = 5.0):
        self.significance_threshold = significance_threshold
        self.percent_threshold = percent_threshold
        self.baseline_metrics: Dict[str, List[float]] = {}

    def set_baseline(self, metric_name: str, values: List[float]):
        self.baseline_metrics[metric_name] = values

    def get_baseline(self, metric_name: str) -> Optional[List[float]]:
        return self.baseline_metrics.get(metric_name)

    def detect_regression(self, metric_name: str, current_values: List[float]) -> RegressionReport:
        baseline_values = self.baseline_metrics.get(metric_name)

        if not baseline_values:
            return RegressionReport(
                metric_name=metric_name,
                baseline_mean=0,
                baseline_std=0,
                current_mean=sum(current_values) / len(current_values) if current_values else 0,
                current_std=0,
                change_percent=0,
                regression_detected=False,
            )

        baseline_mean = sum(baseline_values) / len(baseline_values)
        current_mean = sum(current_values) / len(current_values) if current_values else 0

        baseline_std = self._calculate_std(baseline_values, baseline_mean)
        current_std = self._calculate_std(current_values, current_mean)

        change_percent = ((current_mean - baseline_mean) / baseline_mean * 100) if baseline_mean != 0 else 0

        regression_detected = False
        regression_type = RegressionType.NO_REGRESSION
        severity = "info"

        if abs(change_percent) > self.percent_threshold:
            if current_mean < baseline_mean:
                if change_percent < -10:
                    regression_detected = True
                    regression_type = RegressionType.SIGNIFICANT_DROP
                    severity = "error"
                else:
                    regression_type = RegressionType.MINOR_DROP
                    severity = "warning"
            else:
                regression_type = RegressionType.IMPROVEMENT
                severity = "info"

        p_value = self._t_test(baseline_values, current_values)
        if p_value and p_value < self.significance_threshold and change_percent < 0:
            regression_detected = True
            severity = "error"

        alerts = []
        if regression_detected:
            alerts.append(
                RegressionAlert(
                    metric_name=metric_name,
                    regression_type=regression_type,
                    current_value=current_mean,
                    baseline_value=baseline_mean,
                    change_percent=change_percent,
                    p_value=p_value,
                    severity=severity,
                )
            )

        return RegressionReport(
            metric_name=metric_name,
            baseline_mean=baseline_mean,
            baseline_std=baseline_std,
            current_mean=current_mean,
            current_std=current_std,
            change_percent=change_percent,
            regression_detected=regression_detected,
            alerts=alerts,
        )

    def batch_detect_regressions(self, metrics: Dict[str, List[float]]) -> Dict[str, RegressionReport]:
        reports = {}
        for metric_name, current_values in metrics.items():
            reports[metric_name] = self.detect_regression(metric_name, current_values)
        return reports

    def _calculate_std(self, values: List[float], mean: float) -> float:
        if not values or len(values) < 2:
            return 0
        variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
        return variance ** 0.5

    def _t_test(self, baseline: List[float], current: List[float]) -> Optional[float]:
        try:
            from scipy import stats

            if len(baseline) < 2 or len(current) < 2:
                return None

            t_stat, p_value = stats.ttest_ind(baseline, current)
            return p_value
        except Exception:
            return None

    def generate_report(self, regression_reports: Dict[str, RegressionReport]) -> str:
        lines = ["Regression Detection Report", "=" * 40]

        total_regressions = sum(1 for r in regression_reports.values() if r.regression_detected)
        lines.append(f"Total Regressions Detected: {total_regressions}/{len(regression_reports)}")
        lines.append("")

        for metric_name, report in regression_reports.items():
            lines.append(f"Metric: {metric_name}")
            lines.append(f"  Baseline Mean: {report.baseline_mean:.2f}")
            lines.append(f"  Current Mean: {report.current_mean:.2f}")
            lines.append(f"  Change: {report.change_percent:.2f}%")
            lines.append(f"  Regression: {'YES' if report.regression_detected else 'NO'}")

            if report.alerts:
                for alert in report.alerts:
                    lines.append(f"    Alert: {alert.regression_type.value} (severity: {alert.severity})")
            lines.append("")

        return "\n".join(lines)

    def get_high_severity_alerts(self, regression_reports: Dict[str, RegressionReport]) -> List[RegressionAlert]:
        alerts = []
        for report in regression_reports.values():
            alerts.extend([a for a in report.alerts if a.severity == "error"])
        return alerts
