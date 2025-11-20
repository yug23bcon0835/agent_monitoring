import pytest
import os
import shutil
import time
from datetime import datetime, timedelta
from typing import Dict, Any
import threading

# --- Core Imports ---
from telemetry.collector import TelemetryCollector
from telemetry.exporters import MetricsExporter
from telemetry.events import Event
from data_engineering.database_manager import DatabaseManager
from data_engineering.analytics_engine import AnalyticsEngine
from data_engineering.etl_pipeline import ETLPipeline
from agent_registry.registry import AgentRegistry
from agent_registry.agent_metadata import AgentMetadata
from eval_pipeline.benchmark_suite import BenchmarkSuite, TestCase
from eval_pipeline.quality_metrics import QualityEvaluator
from eval_pipeline.performance_metrics import PerformanceEvaluator
from eval_pipeline.regression_detector import RegressionDetector
from alerting.alert_manager import AlertManager
from alerting.rules_engine import Rule, RulesEngine
from alerting.handlers import AlertHandler

# --- Test Constants ---
TEST_DB_URL = "sqlite:///test_monitoring.db"
TEST_OUTPUT_DIR = "./test_outputs"

# --- Custom Mocks/Helpers ---

class MockAlertHandler(AlertHandler):
    """Captures alerts in memory for testing"""
    def __init__(self):
        super().__init__("mock_handler")
        self.captured_alerts = []

    def send(self, alert: Dict[str, Any]) -> bool:
        self.captured_alerts.append(alert)
        return True

class InMemoryExporter(MetricsExporter):
    """Captures exported metrics in memory"""
    def __init__(self):
        self.exported_metrics = []
        self.exported_events = []

    def export(self, metrics: Dict) -> bool:
        self.exported_metrics.append(metrics)
        return True

    def export_events(self, events: list) -> bool:
        self.exported_events.extend(events)
        return True

# --- Fixtures ---

@pytest.fixture(scope="function")
def clean_environment():
    """Setup and teardown for test environment"""
    # Cleanup before test
    if os.path.exists("test_monitoring.db"):
        os.remove("test_monitoring.db")
    if os.path.exists(TEST_OUTPUT_DIR):
        shutil.rmtree(TEST_OUTPUT_DIR)
    os.makedirs(TEST_OUTPUT_DIR, exist_ok=True)

    yield

    # Cleanup after test
    if os.path.exists("test_monitoring.db"):
        os.remove("test_monitoring.db")
    if os.path.exists(TEST_OUTPUT_DIR):
        shutil.rmtree(TEST_OUTPUT_DIR)

@pytest.fixture
def db_manager(clean_environment):
    db = DatabaseManager(TEST_DB_URL)
    db.create_tables()
    yield db
    db.close()

@pytest.fixture
def collector():
    col = TelemetryCollector(export_interval=1)  # Fast interval for testing
    exporter = InMemoryExporter()
    col.add_exporter(exporter)
    col.start()
    yield col, exporter
    col.stop()

# --- Integration Tests ---

def test_full_platform_lifecycle(db_manager, collector):
    """
    Tests the complete lifecycle of the monitoring platform:
    Registry -> Telemetry -> Data Engineering -> Evaluation -> Analytics -> Alerting
    """
    col, exporter = collector
    
    # ==========================================
    # 1. Agent Registry: Register a new agent
    # ==========================================
    registry = AgentRegistry()
    metadata = AgentMetadata(
        name="test_agent_v1",
        version="1.0.0",
        model_type="llm",
        provider="openai_mock",
        capabilities=["chat", "summarization"]
    )
    agent_key = registry.register_agent(metadata)
    
    assert agent_key == "test_agent_v1:1.0.0"
    assert registry.get_agent("test_agent_v1", "1.0.0") is not None
    
    # Sync agent to DB
    db_agent = db_manager.add_agent(
        name=metadata.name,
        version=metadata.version,
        model_type=metadata.model_type,
        provider=metadata.provider,
        metadata=metadata.to_dict()
    )
    assert db_agent.id is not None

    # ==========================================
    # 2. Telemetry: Simulate Execution
    # ==========================================
    print("\n[Test] Simulating agent execution...")
    
    # Simulate a successful run
    col.record_agent_execution(
        agent_id=db_agent.id,
        duration_ms=250.0,
        success=True,
        tokens_used=150,
        metadata={"input_size": 50}
    )
    
    # Simulate LLM call inside the agent
    col.record_llm_call(
        model="gpt-4",
        prompt_tokens=100,
        completion_tokens=50,
        latency_ms=1200.0,
        cost=0.03
    )
    
    # Simulate a tool call
    col.record_tool_execution(
        tool_name="web_search",
        duration_ms=500.0,
        success=True
    )

    # Force export to ensure memory exporter catches it
    col.export_all()
    
    # Verify Telemetry
    assert len(exporter.exported_metrics) > 0
    assert len(exporter.exported_events) > 0
    
    # Verify specific metrics exist
    latest_metrics = exporter.exported_metrics[-1]
    assert "agent_execution_duration" in latest_metrics
    assert "llm_latency_ms" in latest_metrics

    # ==========================================
    # 3. Data Engineering: Store & ETL
    # ==========================================
    print("\n[Test] Running Data Engineering pipeline...")
    
    # Manually store execution in DB (simulating application persistence layer)
    # In a real app, the collector might push to DB, or app logs to DB directly.
    execution = db_manager.add_execution(
        agent_id=db_agent.id,
        input_data="Explain quantum computing",
        output_data="Quantum computing uses qubits...",
        duration_ms=250.0,
        tokens_used=150,
        success=True
    )
    
    db_manager.add_metric(execution.id, "latency_ms", 250.0)
    db_manager.add_metric(execution.id, "tokens", 150.0)
    
    # Verify DB Storage
    executions = db_manager.get_executions(agent_id=db_agent.id)
    assert len(executions) == 1
    assert executions[0].tokens_used == 150

    # Run ETL Pipeline (Transform raw data)
    etl = ETLPipeline(db_manager)
    
    # Define a simple transformer
    def normalize_tokens(record):
        return {
            "execution_id": record.get("id"),  # Map 'id' from execution to 'execution_id'
            "metric_name": "tokens_k",         # Define the new metric name
            "value": record.get("tokens_used", 0) / 1000.0,
            "tags": {"source": "etl_pipeline", "model": record.get("metadata", {}).get("model_type", "unknown")}
        }
        
    etl.register_transformer("normalize", normalize_tokens)
    
    # Run ETL job (Extract executions -> Transform -> Load back as metrics or derived table)
    # Here we just verify the pipeline runs successfully
    job = etl.run_pipeline(source="executions", target="metrics", transformer="normalize")
    if job.status != "SUCCESS":
        print(f"ETL Job Failed with error: {job.error}")
        
    assert job.status == "SUCCESS"

    # ==========================================
    # 4. Evaluation Pipeline
    # ==========================================
    print("\n[Test] Running Evaluation Suite...")
    
    suite = BenchmarkSuite("test_benchmark_001")
    
    # Add evaluators
    suite.add_evaluator("quality", QualityEvaluator())
    suite.add_evaluator("performance", PerformanceEvaluator())
    
    # Add test case
    suite.add_test_case(TestCase(
        test_id="tc_001",
        input_data="What is 2+2?",
        expected_output="4",
        metadata={"latency_ms": 100, "token_usage": 10}
    ))
    
    # Run evaluation
    results = suite.run()
    
    assert results.execution_time_ms >= 0
    
    # Store results in DB
    db_manager.add_evaluation_run(
        benchmark_id=results.benchmark_id,
        status="completed",
        results=results.to_dict()
    )
    
    saved_runs = db_manager.get_evaluation_runs(benchmark_id=results.benchmark_id)
    assert len(saved_runs) == 1

    # ==========================================
    # 5. Analytics & Regression
    # ==========================================
    print("\n[Test] Checking Analytics & Regression...")
    
    analytics = AnalyticsEngine(db_manager)
    
    # Check execution stats
    stats = analytics.get_execution_statistics(agent_id=db_agent.id)
    assert stats["total_executions"] == 1
    assert stats["avg_duration_ms"] == 250.0
    
    # Regression Detection
    detector = RegressionDetector()
    
    # Set baseline (better performance)
    baseline_latency = [200.0, 210.0, 205.0]
    detector.set_baseline("latency", baseline_latency)
    
    # Current performance (worse)
    current_latency = [250.0, 260.0, 255.0]
    
    report = detector.detect_regression("latency", current_latency)
    
    # Should detect regression (increase in latency)
    # Note: In regression detector logic, 'increase' might be bad depending on metric.
    # Assuming 'latency' implies lower is better, passing higher numbers usually triggers alerts 
    # if configured, though the generic detector checks for significant deviation.
    assert report.change_percent > 0  # Latency increased
    
    # ==========================================
    # 6. Alerting System
    # ==========================================
    print("\n[Test] Testing Alert System...")
    
    alert_manager = AlertManager()
    rules_engine = RulesEngine()
    
    # Create a rule: Alert if latency > 200ms
    rule = Rule(
        rule_id="high_latency",
        metric_name="latency_ms",
        operator=">",
        threshold=200.0,
        duration_seconds=0,
        severity="warning"
    )
    rules_engine.add_rule(rule)
    
    # Mock handler
    mock_handler = MockAlertHandler()
    alert_manager.add_rule(rule)
    
    # In a real scenario, we connect alert manager handlers
    # Here we simulate the flow:
    # 1. Evaluate metrics
    # 2. Create alert if rule triggers
    # 3. Send via handler
    
    metrics_snapshot = {"latency_ms": 250.0} # From our execution
    triggered_rules = rules_engine.evaluate_all(metrics_snapshot)
    
    assert len(triggered_rules) == 1
    assert triggered_rules[0].rule_id == "high_latency"
    
    if triggered_rules:
        alert = alert_manager.create_alert(
            rule_id=triggered_rules[0].rule_id,
            severity=triggered_rules[0].severity,
            message=f"High latency detected: {metrics_snapshot['latency_ms']}ms"
        )
        
        # Send alert
        mock_handler.send(alert.to_dict())
        
    assert len(mock_handler.captured_alerts) == 1
    assert mock_handler.captured_alerts[0]["rule_id"] == "high_latency"
    
    print("\n[Success] Full platform integration test passed!")

def test_telemetry_concurrency():
    """Test thread safety of telemetry collection"""
    col = TelemetryCollector()
    
    def emit_metrics():
        for _ in range(100):
            col.record_agent_execution("concurrent_agent", 100, True)
            
    threads = [threading.Thread(target=emit_metrics) for _ in range(5)]
    
    for t in threads:
        t.start()
        
    for t in threads:
        t.join()
        
    # Verify metrics count
    metric = col.get_metric("agent_execution_duration")
    print(f"Concurrency Test: Metric count = {len(metric.values)}")
    assert len(metric.values) == 500

if __name__ == "__main__":
    # Allow running without pytest
    try:
        # Manual setup for standalone run
        if os.path.exists("test_monitoring.db"): os.remove("test_monitoring.db")
        db = DatabaseManager("sqlite:///test_monitoring.db")
        db.create_tables()
        
        col = TelemetryCollector()
        exporter = InMemoryExporter()
        col.add_exporter(exporter)
        
        print("Running system integration test...")
        test_full_platform_lifecycle(db, (col, exporter))
        
        print("Running concurrency test...")
        test_telemetry_concurrency()
        
        # Cleanup
        db.close()
        if os.path.exists("test_monitoring.db"): os.remove("test_monitoring.db")
        print("All tests passed successfully.")
        
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()