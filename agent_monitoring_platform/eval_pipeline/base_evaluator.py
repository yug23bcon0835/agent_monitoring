from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime


@dataclass
class EvaluationResult:
    evaluator_name: str
    test_case_id: str
    score: float
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_passed(self, threshold: float = 0.7) -> bool:
        return self.score >= threshold and self.error is None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "evaluator_name": self.evaluator_name,
            "test_case_id": self.test_case_id,
            "score": self.score,
            "passed": self.is_passed(),
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
            "error": self.error,
            "metadata": self.metadata,
        }


class BaseEvaluator(ABC):
    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.requires_ground_truth = True
        self.metric_definitions = {}

    @abstractmethod
    def evaluate(self, output: Any, expected: Optional[Any] = None, context: Optional[Dict[str, Any]] = None) -> EvaluationResult:
        pass

    def get_metrics(self) -> Dict[str, str]:
        return self.metric_definitions

    def batch_evaluate(
        self, outputs: List[Any], expected: Optional[List[Any]] = None, contexts: Optional[List[Dict[str, Any]]] = None
    ) -> List[EvaluationResult]:
        results = []
        for i, output in enumerate(outputs):
            exp = expected[i] if expected else None
            ctx = contexts[i] if contexts else None
            result = self.evaluate(output, exp, ctx)
            results.append(result)
        return results

    def get_summary(self, results: List[EvaluationResult]) -> Dict[str, Any]:
        if not results:
            return {}

        passed = sum(1 for r in results if r.is_passed())
        scores = [r.score for r in results if r.error is None]

        return {
            "total": len(results),
            "passed": passed,
            "failed": len(results) - passed,
            "pass_rate": passed / len(results) if results else 0,
            "avg_score": sum(scores) / len(scores) if scores else 0,
            "min_score": min(scores) if scores else 0,
            "max_score": max(scores) if scores else 0,
            "errors": sum(1 for r in results if r.error is not None),
        }

    def supports_ground_truth(self) -> bool:
        return self.requires_ground_truth
