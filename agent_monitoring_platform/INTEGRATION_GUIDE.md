# Integration Guide - Agent Monitoring Platform

## Quick Integration Checklist

This guide shows how to integrate the monitoring platform with your agent system.

## 1. Installation

```bash
cd agent_monitoring_platform
pip install -r requirements.txt
# or
pip install -e .
```

## 2. Basic Setup

### Initialize Telemetry

```python
from telemetry.collector import TelemetryCollector
from telemetry.exporters import JSONExporter

# Create collector
collector = TelemetryCollector()

# Add exporter
collector.add_exporter(JSONExporter("./metrics"))

# Start collection
collector.start()
```

### Initialize Database

```python
from data_engineering.database_manager import DatabaseManager

# Create database
db = DatabaseManager("sqlite:///monitoring.db")
db.create_tables()
```

## 3. Instrument Your Agent

### Track Agent Execution

```python
import time

# Before agent execution
start_time = time.time()

# Your agent code here
result = agent.execute(input_data)

# After execution
duration_ms = (time.time() - start_time) * 1000

# Record metrics
collector.record_agent_execution(
    agent_id="my_agent",
    duration_ms=duration_ms,
    success=True,
    tokens_used=150,
    metadata={"model": "gpt-3.5-turbo"}
)
```

### Track LLM Calls

```python
# Before LLM call
start_time = time.time()

# Your LLM call here
response = llm.generate(prompt, max_tokens=100)

# After call
latency_ms = (time.time() - start_time) * 1000

# Record metrics
collector.record_llm_call(
    model="gpt-3.5-turbo",
    prompt_tokens=len(prompt.split()),
    completion_tokens=len(response.split()),
    latency_ms=latency_ms,
    cost=0.001
)
```

### Track Tool Execution

```python
# Before tool call
start_time = time.time()

# Your tool call here
result = search_tool.search(query)

# After call
duration_ms = (time.time() - start_time) * 1000

# Record metrics
collector.record_tool_execution(
    tool_name="search",
    duration_ms=duration_ms,
    success=True
)
```

## 4. Integration with LangGraph

### Wrap Agent with Tracing

```python
from telemetry.agent_tracer import AgentTracer

tracer = AgentTracer(
    metrics_registry=collector.metrics_registry,
    event_emitter=collector.event_emitter
)

# In your LangGraph workflow:
for step in workflow.steps:
    trace_id = tracer.start_trace(agent_id="my_agent")
    
    # Execute step
    result = await step.execute()
    
    tracer.end_trace(trace_id)
```

### Track Tool Calls

```python
def tool_wrapper(tool_func):
    def wrapped(*args, **kwargs):
        span_id = tracer.trace_tool_call(
            tool_name=tool_func.__name__,
            tool_input=args[0] if args else None
        )
        try:
            result = tool_func(*args, **kwargs)
            tracer.end_span(span_id, status="OK")
            return result
        except Exception as e:
            tracer.end_span(span_id, status="ERROR", error=str(e))
            raise
    return wrapped
```

## 5. Setup Evaluations

### Define Quality Benchmarks

```python
from eval_pipeline.benchmark_suite import BenchmarkSuite, TestCase
from eval_pipeline.quality_metrics import QualityEvaluator
from eval_pipeline.performance_metrics import PerformanceEvaluator

suite = BenchmarkSuite("my_benchmark")

# Add evaluators
suite.add_evaluator("quality", QualityEvaluator())
suite.add_evaluator("performance", PerformanceEvaluator())

# Add test cases
test_cases = [
    TestCase(
        test_id="test_1",
        input_data="What is AI?",
        expected_output="AI is...",
        metadata={"category": "definitions"}
    ),
    # Add more test cases
]

for tc in test_cases:
    suite.add_test_case(tc)

# Run evaluation
results = suite.run()
```

### Store Results

```python
eval_run = db.add_evaluation_run(
    benchmark_id=results.benchmark_id,
    status="completed",
    results=results.to_dict(),
    metadata={"agent_version": "1.0"}
)
```

## 6. Setup Monitoring Queries

### Query Metrics

```python
from data_engineering.analytics_engine import AnalyticsEngine
from datetime import datetime, timedelta

analytics = AnalyticsEngine(db)

# Get time-series metrics
timeseries = analytics.get_time_series(
    metric_name="agent_execution_duration",
    start_time=datetime.utcnow() - timedelta(hours=1),
    end_time=datetime.utcnow(),
    granularity="1h"
)

# Get aggregations
agg = analytics.get_aggregations(
    metric_name="agent_execution_duration",
    group_by="model"
)

# Detect anomalies
anomalies = analytics.detect_anomalies(
    metric_name="agent_execution_duration",
    window_size=10
)
```

## 7. Setup Alerts

### Define Alert Rules

```python
from alerting.alert_manager import AlertManager
from alerting.rules_engine import Rule

alert_manager = AlertManager()

# Add alert rule
rule = Rule(
    rule_id="high_latency",
    metric_name="agent_execution_duration",
    operator=">",
    threshold=1000,
    duration_seconds=300,
    severity="error"
)

alert_manager.add_rule(rule)
```

### Handle Alerts

```python
from alerting.handlers import SlackHandler, EmailHandler

# Add notification handlers
slack_handler = SlackHandler("https://hooks.slack.com/...")
email_handler = EmailHandler("alerts@company.com")

alert_manager.add_handler(slack_handler)
alert_manager.add_handler(email_handler)
```

## 8. Query Database

### Get Agent History

```python
# Get all agents
agents = db.get_agents()

# Get specific agent
agent = db.get_agent("agent_id")

# Get execution history
executions = db.get_executions(agent_id="agent_id", limit=100)

# Get metrics
metrics = db.get_metrics(metric_name="latency_ms", limit=1000)
```

## 9. Export and Analysis

### Export Metrics

```python
# Export to JSON
collector.export_to_file("./output")

# Export evaluation results
results_json = suite.export_results(format="json")
results_csv = suite.export_results(format="csv")
```

### Generate Reports

```python
from eval_pipeline.regression_detector import RegressionDetector

detector = RegressionDetector()
detector.set_baseline("latency_ms", baseline_values)

report = detector.detect_regression("latency_ms", current_values)
summary = detector.generate_report({...})
print(summary)
```

## 10. Full Integration Example

```python
import time
from telemetry.collector import TelemetryCollector
from data_engineering.database_manager import DatabaseManager
from eval_pipeline.benchmark_suite import BenchmarkSuite, TestCase
from eval_pipeline.quality_metrics import QualityEvaluator

# Setup
collector = TelemetryCollector()
collector.start()

db = DatabaseManager()
db.create_tables()

# Register agent
agent = db.add_agent(
    name="my_agent",
    version="1.0",
    model_type="llm",
    provider="openai"
)

# Simulate execution
for i in range(10):
    start = time.time()
    
    # Your agent logic here
    result = "Agent response"
    
    duration_ms = (time.time() - start) * 1000
    
    # Record execution
    collector.record_agent_execution(
        agent_id=agent.id,
        duration_ms=duration_ms,
        success=True,
        tokens_used=100
    )
    
    # Store in database
    execution = db.add_execution(
        agent_id=agent.id,
        input_data=f"input_{i}",
        output_data=result,
        duration_ms=duration_ms,
        tokens_used=100,
        success=True
    )

# Run evaluation
suite = BenchmarkSuite()
suite.add_evaluator("quality", QualityEvaluator())
suite.add_test_case(TestCase(
    test_id="test_1",
    input_data="test input",
    expected_output="expected output"
))
results = suite.run()

# Store results
db.add_evaluation_run(
    benchmark_id=results.benchmark_id,
    status="completed",
    results=results.to_dict()
)

# Cleanup
collector.stop()
db.close()

print("✅ Integration complete!")
```

## Troubleshooting

### Issue: Metrics not appearing
- Check if collector is running: `collector.is_running`
- Verify exporter is configured: `collector.exporters`
- Check database tables exist: `db.get_statistics()`

### Issue: Slow metric collection
- Reduce export interval: `export_interval=30`
- Enable sampling in telemetry
- Use connection pooling for database

### Issue: Memory growth
- Set retention policy: `collector.set_retention_days(7)`
- Clear old spans: `tracer.clear_spans()`
- Cleanup database: `db.cleanup_old_data(7)`

## Next Steps

1. **Deploy Dashboard**: Run `streamlit run dashboard/streamlit_app.py`
2. **Configure Alerts**: Set up Slack/Email notifications
3. **Optimize Queries**: Create database indexes for frequent queries
4. **Scale Infrastructure**: Switch to PostgreSQL for production
5. **Custom Metrics**: Extend evaluators for your use cases

---

For more information, see:
- `ARCHITECTURE.md` - System design
- `README.md` - Quick start
- `examples/` - Usage examples
