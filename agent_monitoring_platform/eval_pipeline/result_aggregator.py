from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from .base_evaluator import EvaluationResult


class AggregationType(str, Enum):
    MEAN = "mean"
    MEDIAN = "median"
    MIN = "min"
    MAX = "max"
    P95 = "p95"
    P99 = "p99"


@dataclass
class AggregatedMetrics:
    metric_name: str
    total_count: int
    passed_count: int
    failed_count: int
    error_count: int
    pass_rate: float
    mean_score: float
    median_score: float
    min_score: float
    max_score: float
    p95_score: float
    p99_score: float
    std_dev: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metric_name": self.metric_name,
            "total_count": self.total_count,
            "passed_count": self.passed_count,
            "failed_count": self.failed_count,
            "error_count": self.error_count,
            "pass_rate": self.pass_rate,
            "scores": {
                "mean": self.mean_score,
                "median": self.median_score,
                "min": self.min_score,
                "max": self.max_score,
                "p95": self.p95_score,
                "p99": self.p99_score,
                "std_dev": self.std_dev,
            },
        }


class ResultAggregator:
    def __init__(self):
        self.results: List[EvaluationResult] = []

    def add_result(self, result: EvaluationResult):
        self.results.append(result)

    def add_results(self, results: List[EvaluationResult]):
        self.results.extend(results)

    def aggregate(self, evaluator_name: Optional[str] = None) -> AggregatedMetrics:
        if evaluator_name:
            filtered_results = [r for r in self.results if r.evaluator_name == evaluator_name]
        else:
            filtered_results = self.results

        if not filtered_results:
            return AggregatedMetrics(
                metric_name=evaluator_name or "all",
                total_count=0,
                passed_count=0,
                failed_count=0,
                error_count=0,
                pass_rate=0,
                mean_score=0,
                median_score=0,
                min_score=0,
                max_score=0,
                p95_score=0,
                p99_score=0,
                std_dev=0,
            )

        passed = sum(1 for r in filtered_results if r.is_passed())
        failed = sum(1 for r in filtered_results if not r.is_passed() and r.error is None)
        errors = sum(1 for r in filtered_results if r.error is not None)

        scores = [r.score for r in filtered_results if r.error is None]
        scores.sort()

        mean_score = sum(scores) / len(scores) if scores else 0
        median_score = self._calculate_median(scores)
        min_score = min(scores) if scores else 0
        max_score = max(scores) if scores else 0
        p95_score = self._calculate_percentile(scores, 95)
        p99_score = self._calculate_percentile(scores, 99)
        std_dev = self._calculate_std_dev(scores, mean_score)
        pass_rate = passed / len(filtered_results) if filtered_results else 0

        return AggregatedMetrics(
            metric_name=evaluator_name or "all",
            total_count=len(filtered_results),
            passed_count=passed,
            failed_count=failed,
            error_count=errors,
            pass_rate=pass_rate,
            mean_score=mean_score,
            median_score=median_score,
            min_score=min_score,
            max_score=max_score,
            p95_score=p95_score,
            p99_score=p99_score,
            std_dev=std_dev,
        )

    def get_aggregations_by_evaluator(self) -> Dict[str, AggregatedMetrics]:
        evaluators = set(r.evaluator_name for r in self.results)
        return {evaluator: self.aggregate(evaluator) for evaluator in evaluators}

    def get_aggregations_by_test_case(self) -> Dict[str, AggregatedMetrics]:
        test_cases = set(r.test_case_id for r in self.results)
        aggregations = {}

        for test_case_id in test_cases:
            filtered = [r for r in self.results if r.test_case_id == test_case_id]
            scores = [r.score for r in filtered if r.error is None]

            mean_score = sum(scores) / len(scores) if scores else 0
            aggregations[test_case_id] = AggregatedMetrics(
                metric_name=f"test_{test_case_id}",
                total_count=len(filtered),
                passed_count=sum(1 for r in filtered if r.is_passed()),
                failed_count=sum(1 for r in filtered if not r.is_passed() and r.error is None),
                error_count=sum(1 for r in filtered if r.error is not None),
                pass_rate=sum(1 for r in filtered if r.is_passed()) / len(filtered) if filtered else 0,
                mean_score=mean_score,
                median_score=self._calculate_median(scores),
                min_score=min(scores) if scores else 0,
                max_score=max(scores) if scores else 0,
                p95_score=self._calculate_percentile(scores, 95),
                p99_score=self._calculate_percentile(scores, 99),
                std_dev=self._calculate_std_dev(scores, mean_score),
            )

        return aggregations

    def get_comparison_metrics(self, evaluator1: str, evaluator2: str) -> Dict[str, Any]:
        agg1 = self.aggregate(evaluator1)
        agg2 = self.aggregate(evaluator2)

        return {
            "evaluator1": {
                "name": evaluator1,
                "mean_score": agg1.mean_score,
                "pass_rate": agg1.pass_rate,
            },
            "evaluator2": {
                "name": evaluator2,
                "mean_score": agg2.mean_score,
                "pass_rate": agg2.pass_rate,
            },
            "diff_mean_score": agg1.mean_score - agg2.mean_score,
            "diff_pass_rate": agg1.pass_rate - agg2.pass_rate,
            "winner": evaluator1 if agg1.mean_score > agg2.mean_score else evaluator2,
        }

    def export_to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "total_results": len(self.results),
            "by_evaluator": {
                name: agg.to_dict() for name, agg in self.get_aggregations_by_evaluator().items()
            },
            "by_test_case": {
                test_id: agg.to_dict() for test_id, agg in self.get_aggregations_by_test_case().items()
            },
        }

    def _calculate_median(self, values: List[float]) -> float:
        if not values:
            return 0
        sorted_values = sorted(values)
        n = len(sorted_values)
        if n % 2 == 0:
            return (sorted_values[n // 2 - 1] + sorted_values[n // 2]) / 2
        return sorted_values[n // 2]

    def _calculate_percentile(self, values: List[float], percentile: float) -> float:
        if not values:
            return 0
        sorted_values = sorted(values)
        index = int(len(sorted_values) * percentile / 100)
        return sorted_values[min(index, len(sorted_values) - 1)]

    def _calculate_std_dev(self, values: List[float], mean: float) -> float:
        if not values or len(values) < 2:
            return 0
        variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
        return variance ** 0.5

    def clear(self):
        self.results.clear()
