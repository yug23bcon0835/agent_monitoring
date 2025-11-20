from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime
import time

from .base_evaluator import BaseEvaluator, EvaluationResult


@dataclass
class PerformanceMetrics:
    latency_ms: float
    throughput: float
    memory_mb: float
    cpu_percent: float
    error_rate: float
    timeout_rate: float
    retry_rate: float
    cost_per_request: float
    overall_score: float

    def to_dict(self) -> Dict[str, float]:
        return {
            "latency_ms": self.latency_ms,
            "throughput": self.throughput,
            "memory_mb": self.memory_mb,
            "cpu_percent": self.cpu_percent,
            "error_rate": self.error_rate,
            "timeout_rate": self.timeout_rate,
            "retry_rate": self.retry_rate,
            "cost_per_request": self.cost_per_request,
            "overall_score": self.overall_score,
        }


class PerformanceEvaluator(BaseEvaluator):
    def __init__(self):
        super().__init__("performance_evaluator", "Evaluates agent performance metrics")
        self.requires_ground_truth = False
        self.metric_definitions = {
            "latency": "Response time in milliseconds",
            "throughput": "Requests per second",
            "memory": "Memory usage in MB",
            "cpu": "CPU utilization percentage",
            "error_rate": "Percentage of failed requests",
            "timeout_rate": "Percentage of timed out requests",
            "retry_rate": "Percentage of retried requests",
        }

    def evaluate(self, output: Any, expected: Optional[Any] = None, context: Optional[Dict[str, Any]] = None) -> EvaluationResult:
        try:
            context = context or {}
            metrics = PerformanceMetrics(
                latency_ms=context.get("latency_ms", 0),
                throughput=context.get("throughput", 0),
                memory_mb=context.get("memory_mb", 0),
                cpu_percent=context.get("cpu_percent", 0),
                error_rate=context.get("error_rate", 0),
                timeout_rate=context.get("timeout_rate", 0),
                retry_rate=context.get("retry_rate", 0),
                cost_per_request=context.get("cost_per_request", 0),
                overall_score=0,
            )

            overall_score = self._calculate_performance_score(metrics)
            metrics.overall_score = overall_score

            return EvaluationResult(
                evaluator_name=self.name,
                test_case_id=context.get("test_id", ""),
                score=overall_score,
                details=metrics.to_dict(),
            )
        except Exception as e:
            return EvaluationResult(
                evaluator_name=self.name,
                test_case_id=context.get("test_id", "") if context else "",
                score=0,
                error=str(e),
            )

    def _calculate_performance_score(self, metrics: PerformanceMetrics) -> float:
        score = 1.0

        if metrics.latency_ms > 5000:
            score -= 0.3
        elif metrics.latency_ms > 1000:
            score -= 0.1

        if metrics.error_rate > 0.1:
            score -= 0.3
        elif metrics.error_rate > 0.01:
            score -= 0.1

        if metrics.timeout_rate > 0.05:
            score -= 0.2

        if metrics.cpu_percent > 80:
            score -= 0.1

        if metrics.memory_mb > 1000:
            score -= 0.1

        return max(0, min(1.0, score))


class LatencyEvaluator(BaseEvaluator):
    def __init__(self, threshold_ms: float = 1000):
        super().__init__("latency_evaluator", f"Evaluates latency (threshold: {threshold_ms}ms)")
        self.requires_ground_truth = False
        self.threshold_ms = threshold_ms

    def evaluate(self, output: Any, expected: Optional[Any] = None, context: Optional[Dict[str, Any]] = None) -> EvaluationResult:
        context = context or {}
        latency_ms = context.get("latency_ms", 0)
        score = 1.0 - min(1.0, latency_ms / self.threshold_ms)
        return EvaluationResult(
            evaluator_name=self.name,
            test_case_id=context.get("test_id", ""),
            score=score,
            details={"latency_ms": latency_ms, "threshold_ms": self.threshold_ms},
        )


class ThroughputEvaluator(BaseEvaluator):
    def __init__(self, min_throughput: float = 10):
        super().__init__("throughput_evaluator", f"Evaluates throughput (target: {min_throughput} req/sec)")
        self.requires_ground_truth = False
        self.min_throughput = min_throughput

    def evaluate(self, output: Any, expected: Optional[Any] = None, context: Optional[Dict[str, Any]] = None) -> EvaluationResult:
        context = context or {}
        throughput = context.get("throughput", 0)
        score = min(1.0, throughput / self.min_throughput) if self.min_throughput > 0 else 0
        return EvaluationResult(
            evaluator_name=self.name,
            test_case_id=context.get("test_id", ""),
            score=score,
            details={"throughput": throughput, "min_throughput": self.min_throughput},
        )


class ErrorRateEvaluator(BaseEvaluator):
    def __init__(self, max_error_rate: float = 0.01):
        super().__init__("error_rate_evaluator", f"Evaluates error rate (max: {max_error_rate*100}%)")
        self.requires_ground_truth = False
        self.max_error_rate = max_error_rate

    def evaluate(self, output: Any, expected: Optional[Any] = None, context: Optional[Dict[str, Any]] = None) -> EvaluationResult:
        context = context or {}
        error_rate = context.get("error_rate", 0)
        score = max(0, 1.0 - (error_rate / self.max_error_rate)) if self.max_error_rate > 0 else 0
        return EvaluationResult(
            evaluator_name=self.name,
            test_case_id=context.get("test_id", ""),
            score=score,
            details={"error_rate": error_rate, "max_error_rate": self.max_error_rate},
        )
