from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
import concurrent.futures
import time

from .base_evaluator import BaseEvaluator, EvaluationResult


@dataclass
class TestCase:
    test_id: str
    input_data: Any
    expected_output: Optional[Any] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BenchmarkResult:
    benchmark_id: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    evaluator_results: Dict[str, List[EvaluationResult]] = field(default_factory=dict)
    test_cases: List[TestCase] = field(default_factory=list)
    summaries: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    execution_time_ms: float = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "benchmark_id": self.benchmark_id,
            "timestamp": self.timestamp.isoformat(),
            "evaluators": list(self.evaluator_results.keys()),
            "test_cases_count": len(self.test_cases),
            "summaries": self.summaries,
            "execution_time_ms": self.execution_time_ms,
        }


class BenchmarkSuite:
    def __init__(self, benchmark_id: Optional[str] = None):
        self.benchmark_id = benchmark_id or f"benchmark_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        self.evaluators: Dict[str, BaseEvaluator] = {}
        self.test_cases: List[TestCase] = []
        self.results: Optional[BenchmarkResult] = None
        self.progress_callback: Optional[Callable[[str, int, int], None]] = None
        self.max_workers = 4

    def add_evaluator(self, name: str, evaluator: BaseEvaluator):
        self.evaluators[name] = evaluator

    def remove_evaluator(self, name: str):
        if name in self.evaluators:
            del self.evaluators[name]

    def add_test_case(self, test_case: TestCase):
        self.test_cases.append(test_case)

    def add_test_cases(self, test_cases: List[TestCase]):
        self.test_cases.extend(test_cases)

    def set_progress_callback(self, callback: Callable[[str, int, int], None]):
        self.progress_callback = callback

    def run(self) -> BenchmarkResult:
        start_time = time.perf_counter()
        result = BenchmarkResult(
            benchmark_id=self.benchmark_id,
            test_cases=self.test_cases,
        )

        if not self.evaluators:
            result.execution_time_ms = (time.perf_counter() - start_time) * 1000
            return result

        total_tasks = len(self.evaluators) * len(self.test_cases)
        completed_tasks = 0

        for evaluator_name, evaluator in self.evaluators.items():
            evaluator_results = []

            for test_case in self.test_cases:
                try:
                    context = {
                        "test_id": test_case.test_id,
                        **test_case.metadata,
                    }

                    eval_result = evaluator.evaluate(
                        test_case.input_data,
                        test_case.expected_output,
                        context,
                    )
                    evaluator_results.append(eval_result)

                except Exception as e:
                    evaluator_results.append(
                        EvaluationResult(
                            evaluator_name=evaluator_name,
                            test_case_id=test_case.test_id,
                            score=0,
                            error=str(e),
                        )
                    )

                completed_tasks += 1
                if self.progress_callback:
                    self.progress_callback(f"Evaluating {evaluator_name}", completed_tasks, total_tasks)

            result.evaluator_results[evaluator_name] = evaluator_results
            summary = evaluator.get_summary(evaluator_results)
            result.summaries[evaluator_name] = summary

        result.execution_time_ms = (time.perf_counter() - start_time) * 1000
        self.results = result
        return result

    def run_parallel(self, max_workers: Optional[int] = None) -> BenchmarkResult:
        start_time = time.perf_counter()
        max_workers = max_workers or self.max_workers
        result = BenchmarkResult(
            benchmark_id=self.benchmark_id,
            test_cases=self.test_cases,
        )

        if not self.evaluators:
            result.execution_time_ms = (time.perf_counter() - start_time) * 1000
            return result

        def evaluate_task(evaluator_name: str, test_case: TestCase) -> tuple:
            evaluator = self.evaluators[evaluator_name]
            try:
                context = {
                    "test_id": test_case.test_id,
                    **test_case.metadata,
                }
                eval_result = evaluator.evaluate(
                    test_case.input_data,
                    test_case.expected_output,
                    context,
                )
                return evaluator_name, eval_result
            except Exception as e:
                return evaluator_name, EvaluationResult(
                    evaluator_name=evaluator_name,
                    test_case_id=test_case.test_id,
                    score=0,
                    error=str(e),
                )

        total_tasks = len(self.evaluators) * len(self.test_cases)
        completed_tasks = 0

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            for evaluator_name in self.evaluators:
                for test_case in self.test_cases:
                    future = executor.submit(evaluate_task, evaluator_name, test_case)
                    futures.append(future)

            for future in concurrent.futures.as_completed(futures):
                evaluator_name, eval_result = future.result()
                if evaluator_name not in result.evaluator_results:
                    result.evaluator_results[evaluator_name] = []
                result.evaluator_results[evaluator_name].append(eval_result)

                completed_tasks += 1
                if self.progress_callback:
                    self.progress_callback("Parallel evaluation", completed_tasks, total_tasks)

        for evaluator_name, evaluator in self.evaluators.items():
            if evaluator_name in result.evaluator_results:
                summary = evaluator.get_summary(result.evaluator_results[evaluator_name])
                result.summaries[evaluator_name] = summary

        result.execution_time_ms = (time.time() - start_time) * 1000
        self.results = result
        return result

    def get_results(self) -> Optional[BenchmarkResult]:
        return self.results

    def get_summary(self) -> Dict[str, Any]:
        if not self.results:
            return {}

        return self.results.to_dict()

    def clear_test_cases(self):
        self.test_cases.clear()

    def export_results(self, format: str = "json") -> str:
        if not self.results:
            return ""

        if format == "json":
            import json

            data = {
                "benchmark_id": self.results.benchmark_id,
                "timestamp": self.results.timestamp.isoformat(),
                "summaries": self.results.summaries,
                "execution_time_ms": self.results.execution_time_ms,
            }
            return json.dumps(data, indent=2)
        elif format == "csv":
            import csv
            import io

            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(["Evaluator", "Test Case ID", "Score", "Passed", "Error"])

            for evaluator_name, results in self.results.evaluator_results.items():
                for result in results:
                    writer.writerow([
                        evaluator_name,
                        result.test_case_id,
                        result.score,
                        result.is_passed(),
                        result.error or "",
                    ])

            return output.getvalue()

        return ""
