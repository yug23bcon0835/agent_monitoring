#!/usr/bin/env python3
"""
Basic monitoring example showing how to set up telemetry collection
"""

import time
import random
from telemetry.collector import TelemetryCollector
from telemetry.exporters import JSONExporter


def simulate_agent_execution(collector, agent_id, num_iterations=10):
    """Simulate agent executions and collect metrics"""

    print(f"Starting monitoring for {agent_id}...")

    for i in range(num_iterations):
        print(f"  Iteration {i+1}/{num_iterations}")

        # Simulate agent work
        duration_ms = random.uniform(100, 1000)
        success = random.random() > 0.1
        tokens_used = random.randint(50, 500)
        error_msg = None if success else "Agent execution failed"

        # Record execution
        collector.record_agent_execution(
            agent_id=agent_id,
            duration_ms=duration_ms,
            success=success,
            tokens_used=tokens_used,
            error=error_msg,
        )

        # Simulate LLM calls
        if random.random() > 0.3:
            llm_latency = random.uniform(500, 2000)
            prompt_tokens = random.randint(50, 200)
            completion_tokens = random.randint(20, 100)

            collector.record_llm_call(
                model="gpt-3.5-turbo",
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                latency_ms=llm_latency,
                cost=0.001,
            )

        time.sleep(0.5)

    print("Monitoring completed!")


def main():
    # Initialize collector
    collector = TelemetryCollector(export_interval=30)

    # Add JSON exporter
    json_exporter = JSONExporter(output_dir="./monitoring_output")
    collector.add_exporter(json_exporter)

    # Start collection
    collector.start()

    # Simulate agent executions
    simulate_agent_execution(collector, "agent_demo", num_iterations=10)

    # Get health status
    health = collector.get_health_status()
    print("\nHealth Status:")
    print(f"  Running: {health['is_running']}")
    print(f"  CPU: {health['cpu_percent']:.1f}%")
    print(f"  Memory: {health['memory_percent']:.1f}%")
    print(f"  Metrics: {health['metrics_count']}")
    print(f"  Events: {health['events_count']}")

    # Get summary
    summary = collector.get_all_metrics_summary()
    print("\nMetrics Summary:")
    print(f"  Total Metrics: {len(summary['metrics'])}")
    print(f"  Events by Type: {summary['events']['by_type']}")

    # Stop collection
    collector.stop()

    print("\nDone!")


if __name__ == "__main__":
    main()
