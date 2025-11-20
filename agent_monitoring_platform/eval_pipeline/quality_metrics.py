from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime
import re

from .base_evaluator import BaseEvaluator, EvaluationResult


@dataclass
class QualityMetrics:
    accuracy: float
    relevance: float
    completeness: float
    factuality: float
    coherence: float
    toxicity: float
    overall_score: float

    def to_dict(self) -> Dict[str, float]:
        return {
            "accuracy": self.accuracy,
            "relevance": self.relevance,
            "completeness": self.completeness,
            "factuality": self.factuality,
            "coherence": self.coherence,
            "toxicity": self.toxicity,
            "overall_score": self.overall_score,
        }


class QualityEvaluator(BaseEvaluator):
    def __init__(self):
        super().__init__("quality_evaluator", "Evaluates output quality metrics")
        self.requires_ground_truth = True
        self.metric_definitions = {
            "accuracy": "Exact match or fuzzy match with ground truth",
            "relevance": "Semantic relevance to query",
            "completeness": "Coverage of all required elements",
            "factuality": "Absence of hallucinations",
            "coherence": "Logical consistency and clarity",
            "toxicity": "Absence of harmful content",
        }

    def evaluate(self, output: Any, expected: Optional[Any] = None, context: Optional[Dict[str, Any]] = None) -> EvaluationResult:
        try:
            output_text = str(output) if output else ""
            expected_text = str(expected) if expected else ""

            metrics = QualityMetrics(
                accuracy=self._evaluate_accuracy(output_text, expected_text),
                relevance=self._evaluate_relevance(output_text, context or {}),
                completeness=self._evaluate_completeness(output_text, context or {}),
                factuality=self._evaluate_factuality(output_text),
                coherence=self._evaluate_coherence(output_text),
                toxicity=self._evaluate_toxicity(output_text),
                overall_score=0,
            )

            weights = {
                "accuracy": 0.2,
                "relevance": 0.2,
                "completeness": 0.15,
                "factuality": 0.2,
                "coherence": 0.15,
                "toxicity": 0.1,
            }

            overall_score = sum(getattr(metrics, k) * v for k, v in weights.items())
            metrics.overall_score = overall_score

            return EvaluationResult(
                evaluator_name=self.name,
                test_case_id=context.get("test_id", "") if context else "",
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

    def _evaluate_accuracy(self, output: str, expected: str) -> float:
        if not expected:
            return 0.5

        if output == expected:
            return 1.0

        output_words = set(output.lower().split())
        expected_words = set(expected.lower().split())

        if not expected_words:
            return 0

        intersection = len(output_words & expected_words)
        union = len(output_words | expected_words)

        return intersection / union if union > 0 else 0

    def _evaluate_relevance(self, output: str, context: Dict[str, Any]) -> float:
        query = context.get("query", "")
        if not query:
            return 0.7

        query_words = set(query.lower().split())
        output_words = set(output.lower().split())

        if not query_words:
            return 0.7

        intersection = len(query_words & output_words)
        return min(1.0, intersection / len(query_words))

    def _evaluate_completeness(self, output: str, context: Dict[str, Any]) -> float:
        required_keywords = context.get("required_keywords", [])
        if not required_keywords:
            return 0.8 if output else 0.2

        output_lower = output.lower()
        found = sum(1 for kw in required_keywords if kw.lower() in output_lower)

        return found / len(required_keywords) if required_keywords else 0

    def _evaluate_factuality(self, output: str) -> float:
        hallucination_patterns = [
            r"i'm not sure",
            r"i don't know",
            r"i cannot",
            r"i can't verify",
            r"unknown error",
        ]

        score = 1.0
        for pattern in hallucination_patterns:
            if re.search(pattern, output.lower()):
                score -= 0.2

        return max(0, score)

    def _evaluate_coherence(self, output: str) -> float:
        if not output:
            return 0

        sentences = output.split(".")
        if len(sentences) < 2:
            return 0.7

        avg_length = sum(len(s.split()) for s in sentences) / len(sentences)

        if avg_length < 3 or avg_length > 30:
            return 0.6

        return min(1.0, 0.8 + (avg_length / 50))

    def _evaluate_toxicity(self, output: str) -> float:
        toxic_patterns = [
            r"\b(?:hate|kill|die|violence|abuse)\b",
            r"\b(?:damn|crap|[a-z]*shit)\b",
        ]

        score = 1.0
        for pattern in toxic_patterns:
            if re.search(pattern, output.lower()):
                score -= 0.3

        return max(0, score)


class AccuracyEvaluator(BaseEvaluator):
    def __init__(self):
        super().__init__("accuracy_evaluator", "Evaluates exact accuracy against ground truth")
        self.requires_ground_truth = True

    def evaluate(self, output: Any, expected: Optional[Any] = None, context: Optional[Dict[str, Any]] = None) -> EvaluationResult:
        score = 1.0 if str(output) == str(expected) else 0.0
        return EvaluationResult(
            evaluator_name=self.name,
            test_case_id=context.get("test_id", "") if context else "",
            score=score,
            details={"exact_match": score == 1.0},
        )


class SemanticSimilarityEvaluator(BaseEvaluator):
    def __init__(self):
        super().__init__("semantic_similarity_evaluator", "Evaluates semantic similarity")
        self.requires_ground_truth = True

    def evaluate(self, output: Any, expected: Optional[Any] = None, context: Optional[Dict[str, Any]] = None) -> EvaluationResult:
        try:
            from sentence_transformers import util, SentenceTransformer

            model = SentenceTransformer("all-MiniLM-L6-v2")
            embeddings1 = model.encode(str(output), convert_to_tensor=True)
            embeddings2 = model.encode(str(expected), convert_to_tensor=True)
            score = float(util.pytorch_cos_sim(embeddings1, embeddings2)[0][0])

            return EvaluationResult(
                evaluator_name=self.name,
                test_case_id=context.get("test_id", "") if context else "",
                score=score,
                details={"cosine_similarity": score},
            )
        except ImportError:
            return EvaluationResult(
                evaluator_name=self.name,
                test_case_id=context.get("test_id", "") if context else "",
                score=0,
                error="sentence-transformers not installed",
            )
