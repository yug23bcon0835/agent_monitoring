from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime

from .benchmark_suite import BenchmarkResult


@dataclass
class AgentComparison:
    agent1_id: str
    agent2_id: str
    metrics: Dict[str, Any]
    winner: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent1_id": self.agent1_id,
            "agent2_id": self.agent2_id,
            "metrics": self.metrics,
            "winner": self.winner,
            "timestamp": self.timestamp.isoformat(),
        }


class AgentComparator:
    def __init__(self):
        self.comparisons: List[AgentComparison] = []

    def compare_agents(
        self,
        agent1_id: str,
        agent1_results: BenchmarkResult,
        agent2_id: str,
        agent2_results: BenchmarkResult,
        focus_metrics: Optional[List[str]] = None,
    ) -> AgentComparison:
        metrics = {}

        all_evaluators = set(agent1_results.summaries.keys()) | set(agent2_results.summaries.keys())

        for evaluator in all_evaluators:
            if focus_metrics and evaluator not in focus_metrics:
                continue

            summary1 = agent1_results.summaries.get(evaluator, {})
            summary2 = agent2_results.summaries.get(evaluator, {})

            metrics[evaluator] = {
                "agent1": {
                    "pass_rate": summary1.get("pass_rate", 0),
                    "avg_score": summary1.get("avg_score", 0),
                    "total": summary1.get("total", 0),
                    "errors": summary1.get("errors", 0),
                },
                "agent2": {
                    "pass_rate": summary2.get("pass_rate", 0),
                    "avg_score": summary2.get("avg_score", 0),
                    "total": summary2.get("total", 0),
                    "errors": summary2.get("errors", 0),
                },
                "diff_pass_rate": summary1.get("pass_rate", 0) - summary2.get("pass_rate", 0),
                "diff_avg_score": summary1.get("avg_score", 0) - summary2.get("avg_score", 0),
                "winner": agent1_id if summary1.get("avg_score", 0) > summary2.get("avg_score", 0) else agent2_id,
            }

        agent1_wins = sum(1 for m in metrics.values() if m.get("winner") == agent1_id)
        agent2_wins = sum(1 for m in metrics.values() if m.get("winner") == agent2_id)

        overall_winner = agent1_id if agent1_wins > agent2_wins else agent2_id

        comparison = AgentComparison(
            agent1_id=agent1_id,
            agent2_id=agent2_id,
            metrics=metrics,
            winner=overall_winner,
        )

        self.comparisons.append(comparison)
        return comparison

    def get_strong_areas(self, comparison: AgentComparison, agent_id: str) -> List[str]:
        strong_areas = []
        for metric_name, metric_data in comparison.metrics.items():
            if metric_data.get("winner") == agent_id:
                strong_areas.append(metric_name)
        return strong_areas

    def get_weak_areas(self, comparison: AgentComparison, agent_id: str) -> List[str]:
        weak_areas = []
        for metric_name, metric_data in comparison.metrics.items():
            other_agent = comparison.agent2_id if agent_id == comparison.agent1_id else comparison.agent1_id
            if metric_data.get("winner") == other_agent:
                weak_areas.append(metric_name)
        return weak_areas

    def generate_comparison_report(self, comparison: AgentComparison) -> str:
        lines = [
            f"Agent Comparison Report",
            f"{'=' * 50}",
            f"Agent 1: {comparison.agent1_id}",
            f"Agent 2: {comparison.agent2_id}",
            f"Overall Winner: {comparison.winner}",
            f"",
        ]

        for evaluator, data in comparison.metrics.items():
            lines.append(f"Evaluator: {evaluator}")
            lines.append(f"  Agent 1 - Pass Rate: {data['agent1']['pass_rate']:.2%}, Score: {data['agent1']['avg_score']:.2f}")
            lines.append(f"  Agent 2 - Pass Rate: {data['agent2']['pass_rate']:.2%}, Score: {data['agent2']['avg_score']:.2f}")
            lines.append(f"  Difference - Pass Rate: {data['diff_pass_rate']:.2%}, Score: {data['diff_avg_score']:.2f}")
            lines.append(f"  Winner: {data['winner']}")
            lines.append("")

        agent1_strong = self.get_strong_areas(comparison, comparison.agent1_id)
        agent2_strong = self.get_strong_areas(comparison, comparison.agent2_id)

        if agent1_strong:
            lines.append(f"Agent 1 Strong Areas: {', '.join(agent1_strong)}")
        if agent2_strong:
            lines.append(f"Agent 2 Strong Areas: {', '.join(agent2_strong)}")

        return "\n".join(lines)

    def recommend_improvements(self, comparison: AgentComparison, agent_id: str) -> List[str]:
        recommendations = []
        weak_areas = self.get_weak_areas(comparison, agent_id)

        for weak_area in weak_areas:
            metric_data = comparison.metrics[weak_area]
            other_agent = comparison.agent2_id if agent_id == comparison.agent1_id else comparison.agent1_id
            other_data = metric_data.get("agent2" if agent_id == comparison.agent1_id else "agent1", {})

            diff = abs(metric_data.get("diff_avg_score", 0))
            recommendations.append(
                f"Improve {weak_area}: Currently {diff:.2f} behind {other_agent} "
                f"(other agent score: {other_data.get('avg_score', 0):.2f})"
            )

        return recommendations

    def get_comparison_history(self, agent1_id: str, agent2_id: str) -> List[AgentComparison]:
        return [
            c for c in self.comparisons
            if (c.agent1_id == agent1_id and c.agent2_id == agent2_id) or (c.agent1_id == agent2_id and c.agent2_id == agent1_id)
        ]

    def export_comparisons(self) -> List[Dict[str, Any]]:
        return [c.to_dict() for c in self.comparisons]
