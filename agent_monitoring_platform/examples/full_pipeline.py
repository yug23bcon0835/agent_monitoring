#!/usr/bin/env python3
"""
Full pipeline example demonstrating the complete monitoring platform
"""

from datetime import datetime, timedelta
from telemetry.collector import TelemetryCollector
from telemetry.exporters import JSONExporter
from eval_pipeline.benchmark_suite import BenchmarkSuite, TestCase
from eval_pipeline.quality_metrics import QualityEvaluator, AccuracyEvaluator
from eval_pipeline.performance_metrics import PerformanceEvaluator, LatencyEvaluator
from eval_pipeline.result_aggregator import ResultAggregator
from eval_pipeline.regression_detector import RegressionDetector
from data_engineering.database_manager import DatabaseManager


def setup_telemetry():
    """Set up telemetry collection"""
    collector = TelemetryCollector()
    collector.add_exporter(JSONExporter("./outputs"))

    collector.metrics_registry.histogram(
        "agent_execution_duration",
        "Agent execution duration in ms",
        unit="ms",
    )
    collector.metrics_registry.counter(
        "agent_success_rate",
        "Successful agent executions",
    )

    collector.start()
    return collector


def create_test_cases():
    """Create test cases for evaluation"""
    return [
        TestCase(
            test_id="test_1",
            input_data="What is machine learning?",
            expected_output="Machine learning is a subset of AI...",
            metadata={"query": "What is machine learning?"},
        ),
        TestCase(
            test_id="test_2",
            input_data="Explain neural networks",
            expected_output="Neural networks are computational models...",
            metadata={"query": "Explain neural networks"},
        ),
        TestCase(
            test_id="test_3",
            input_data="How does gradient descent work?",
            expected_output="Gradient descent is an optimization algorithm...",
            metadata={"query": "How does gradient descent work?"},
        ),
    ]


def run_evaluations():
    """Run evaluation suite"""
    print("=" * 60)
    print("RUNNING EVALUATION PIPELINE")
    print("=" * 60)

    suite = BenchmarkSuite("benchmark_full_pipeline")

    # Add evaluators
    suite.add_evaluator("quality", QualityEvaluator())
    suite.add_evaluator("accuracy", AccuracyEvaluator())
    suite.add_evaluator("performance", PerformanceEvaluator())
    suite.add_evaluator("latency", LatencyEvaluator(threshold_ms=1000))

    # Add test cases
    test_cases = create_test_cases()
    for test_case in test_cases:
        suite.add_test_case(test_case)

    # Run evaluation
    results = suite.run()

    print("\nEvaluation Results:")
    print(f"  Benchmark ID: {results.benchmark_id}")
    print(f"  Test Cases: {len(results.test_cases)}")
    print(f"  Execution Time: {results.execution_time_ms:.2f}ms")

    print("\nSummaries by Evaluator:")
    for evaluator, summary in results.summaries.items():
        print(f"\n  {evaluator.upper()}:")
        print(f"    Total: {summary.get('total', 0)}")
        print(f"    Passed: {summary.get('passed', 0)}")
        print(f"    Pass Rate: {summary.get('pass_rate', 0):.2%}")
        print(f"    Avg Score: {summary.get('avg_score', 0):.2f}")

    return results


def run_regression_detection():
    """Demonstrate regression detection"""
    print("\n" + "=" * 60)
    print("RUNNING REGRESSION DETECTION")
    print("=" * 60)

    detector = RegressionDetector(
        significance_threshold=0.05,
        percent_threshold=5.0,
    )

    # Set baseline metrics
    baseline = [100, 105, 102, 98, 103, 101, 99, 102, 104, 100]
    detector.set_baseline("latency_ms", baseline)

    # Simulate current metrics (with some degradation)
    current = [115, 120, 118, 122, 125, 123, 121, 119, 124, 126]

    # Detect regression
    report = detector.detect_regression("latency_ms", current)

    print(f"\nRegression Report for: latency_ms")
    print(f"  Baseline Mean: {report.baseline_mean:.2f}ms")
    print(f"  Current Mean: {report.current_mean:.2f}ms")
    print(f"  Change: {report.change_percent:.2f}%")
    print(f"  Regression Detected: {report.regression_detected}")

    if report.alerts:
        print(f"  Alerts:")
        for alert in report.alerts:
            print(f"    - {alert.regression_type.value} (severity: {alert.severity})")

    return report


def run_data_analytics():
    """Demonstrate data analytics"""
    print("\n" + "=" * 60)
    print("SETTING UP DATA INFRASTRUCTURE")
    print("=" * 60)

    db = DatabaseManager("sqlite:///monitoring_demo.db")
    db.create_tables()

    # Add sample data
    agent = db.add_agent(
        name="demo_agent",
        version="1.0",
        model_type="llm",
        provider="openai",
        metadata={"capabilities": ["qa", "summarization"]},
    )

    print(f"\nAgent Created:")
    print(f"  Name: {agent.name}")
    print(f"  Version: {agent.version}")
    print(f"  ID: {agent.id}")

    # Add executions
    for i in range(5):
        execution = db.add_execution(
            agent_id=agent.id,
            input_data=f"Query {i}",
            output_data=f"Response {i}",
            duration_ms=100 + i * 10,
            tokens_used=150,
            success=True,
        )

        db.add_metric(
            execution_id=execution.id,
            metric_name="latency_ms",
            value=100 + i * 10,
        )

    # Get statistics
    stats = db.get_statistics()
    print(f"\nDatabase Statistics:")
    print(f"  Agents: {stats['agents_count']}")
    print(f"  Executions: {stats['executions_count']}")
    print(f"  Metrics: {stats['metrics_count']}")

    return db


def main():
    print("\n" + "=" * 60)
    print("AGENT MONITORING PLATFORM - FULL PIPELINE DEMO")
    print("=" * 60)

    # Setup telemetry
    collector = setup_telemetry()

    # Run evaluations
    eval_results = run_evaluations()

    # Run regression detection
    regression_report = run_regression_detection()

    # Setup data infrastructure
    db = run_data_analytics()

    # Aggregate results
    print("\n" + "=" * 60)
    print("RESULT AGGREGATION")
    print("=" * 60)

    aggregator = ResultAggregator()
    for evaluator, results in eval_results.evaluator_results.items():
        aggregator.add_results(results)

    aggregations = aggregator.get_aggregations_by_evaluator()
    print("\nAggregated Metrics:")
    for evaluator, agg in aggregations.items():
        print(f"\n  {evaluator}:")
        print(f"    Pass Rate: {agg.pass_rate:.2%}")
        print(f"    Mean Score: {agg.mean_score:.2f}")
        print(f"    Std Dev: {agg.std_dev:.2f}")

    # Cleanup
    print("\n" + "=" * 60)
    print("CLEANING UP")
    print("=" * 60)

    collector.stop()
    db.close()

    print("\n✅ Full pipeline demo completed!")


if __name__ == "__main__":
    main()
