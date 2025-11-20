# Agent Monitoring Platform

A comprehensive monitoring and evaluation platform for AI agents with real-time telemetry, performance evaluation pipeline, and advanced data engineering capabilities.

## 🎯 Platform Overview

The Agent Monitoring Platform provides a production-ready solution for:

- **Real-time Telemetry**: Capture and stream agent metrics, performance data, and system health
- **Evaluation Pipeline**: Automated benchmarking, quality assessment, and performance regression detection
- **Data Engineering**: ETL pipelines, data warehousing, analytics, and reporting
- **Dashboard & Analytics**: Visual monitoring with Streamlit and advanced analytics
- **Agent Registry**: Track agent versions, capabilities, and dependencies
- **Alert System**: Real-time alerts for anomalies and performance issues

## 📁 Project Structure

```
agent_monitoring_platform/
├── README.md                          # This file
├── ARCHITECTURE.md                    # System architecture overview
├── requirements.txt                   # Python dependencies
├── setup.py                          # Package setup
│
├── telemetry/                        # Real-time telemetry collection
│   ├── __init__.py
│   ├── collector.py                  # Base telemetry collector
│   ├── metrics.py                    # Metrics definitions
│   ├── events.py                     # Event schema and handlers
│   ├── exporters.py                  # Export to various backends
│   ├── agent_tracer.py              # Agent execution tracing
│   └── performance_monitor.py        # Real-time performance monitoring
│
├── eval_pipeline/                    # Evaluation and benchmarking
│   ├── __init__.py
│   ├── base_evaluator.py            # Base evaluator class
│   ├── quality_metrics.py            # Quality assessment metrics
│   ├── performance_metrics.py        # Performance benchmarks
│   ├── regression_detector.py        # Performance regression detection
│   ├── benchmark_suite.py            # Benchmark execution engine
│   ├── result_aggregator.py          # Aggregate and analyze results
│   └── comparator.py                 # Compare agent versions
│
├── data_engineering/                 # Data pipelines and warehousing
│   ├── __init__.py
│   ├── database_manager.py           # SQLite/PostgreSQL management
│   ├── etl_pipeline.py               # ETL processing
│   ├── data_models.py                # SQLAlchemy ORM models
│   ├── analytics_engine.py           # Analytics and aggregations
│   ├── data_export.py                # Export functionality
│   └── schema_manager.py             # Database schema management
│
├── agent_registry/                   # Agent management
│   ├── __init__.py
│   ├── registry.py                   # Agent registry
│   ├── agent_metadata.py             # Agent metadata models
│   └── version_manager.py            # Version tracking
│
├── alerting/                         # Alert and notification system
│   ├── __init__.py
│   ├── alert_manager.py              # Alert management
│   ├── rules_engine.py               # Alert rules
│   ├── handlers.py                   # Alert handlers (email, webhook, etc)
│   └── notification_queue.py         # Notification queue
│
├── dashboard/                        # Web dashboards
│   ├── __init__.py
│   ├── streamlit_app.py              # Main Streamlit dashboard
│   ├── pages/
│   │   ├── __init__.py
│   │   ├── telemetry.py              # Telemetry dashboard
│   │   ├── evaluation.py             # Evaluation results
│   │   ├── performance.py            # Performance analytics
│   │   ├── agents.py                 # Agent registry view
│   │   └── alerts.py                 # Alert management
│   └── components/
│       ├── __init__.py
│       ├── charts.py                 # Chart components
│       ├── tables.py                 # Table components
│       └── filters.py                # Filter components
│
├── utils/                            # Utility modules
│   ├── __init__.py
│   ├── config.py                     # Configuration management
│   ├── logging.py                    # Logging setup
│   ├── validators.py                 # Data validation
│   └── helpers.py                    # Helper functions
│
└── examples/                         # Example usage
    ├── basic_monitoring.py           # Basic monitoring example
    ├── full_pipeline.py              # Full pipeline example
    └── custom_evaluator.py           # Custom evaluator example
```

## 🚀 Quick Start

### Installation

```bash
cd agent_monitoring_platform
pip install -r requirements.txt
```

### Basic Usage

```python
from telemetry.collector import TelemetryCollector
from eval_pipeline.benchmark_suite import BenchmarkSuite

# Initialize telemetry
collector = TelemetryCollector()
collector.start()

# Define evaluation suite
suite = BenchmarkSuite()
suite.add_evaluator("quality", quality_evaluator)
suite.add_evaluator("performance", performance_evaluator)

# Run evaluation
results = suite.run()

# Stop telemetry and export data
collector.stop()
collector.export("telemetry.json")
```

### Run Dashboard

```bash
streamlit run dashboard/streamlit_app.py
```

## 🔧 Core Components

### 1. Telemetry System

Captures real-time metrics from agent execution:

- **Agent Execution Traces**: Latency, input/output sizes, execution flow
- **LLM Metrics**: Token usage, API latency, cost tracking
- **System Metrics**: CPU, memory, disk I/O
- **Business Metrics**: User satisfaction, conversion rates, task completion
- **Error Tracking**: Exception rates, failure patterns, recovery times

### 2. Evaluation Pipeline

Automated evaluation framework:

- **Quality Metrics**: Accuracy, relevance, completeness, factuality
- **Performance Metrics**: Latency, throughput, resource utilization
- **User Experience**: Response time, error rate, retry rate
- **Regression Detection**: Compare against baseline versions
- **Multi-agent Comparison**: Benchmark across different models

### 3. Data Engineering

Production data infrastructure:

- **Data Models**: SQLAlchemy ORM for PostgreSQL/SQLite
- **ETL Pipeline**: Ingest, transform, load telemetry data
- **Analytics Engine**: Aggregations, time-series analysis, correlations
- **Data Export**: CSV, Parquet, API endpoints
- **Schema Management**: Auto-migration and versioning

### 4. Agent Registry

Centralized agent management:

- Agent metadata and capabilities
- Version tracking with rollback support
- Dependency management
- Configuration management

### 5. Alert System

Production monitoring alerts:

- Threshold-based alerts
- Anomaly detection
- Multiple notification channels
- Alert history and acknowledgment

## 📊 Supported Metrics

### Agent Execution Metrics
- Latency (min, max, avg, p50, p95, p99)
- Throughput (requests/sec)
- Error rate and error types
- Timeout rate
- Retry rate

### Quality Metrics
- Accuracy against ground truth
- Relevance scores
- Completeness checks
- Hallucination rate
- Citation accuracy

### Resource Metrics
- CPU usage
- Memory consumption
- Disk I/O
- Network bandwidth
- Cost per request

### Business Metrics
- User satisfaction scores
- Task completion rate
- User retention
- Feature adoption
- Revenue impact

## 🔌 Integrations

- **LLM APIs**: OpenAI, Groq, Anthropic, etc.
- **Message Queue**: Redis, RabbitMQ
- **Databases**: PostgreSQL, SQLite, DuckDB
- **Cloud Storage**: S3, GCS, Azure Blob
- **Monitoring**: Prometheus, Grafana
- **Alerting**: PagerDuty, Slack, Email

## 📈 Analytics Features

- Time-series analysis
- Correlation detection
- Anomaly detection
- Trend analysis
- Performance forecasting
- Comparative analysis

## 🛠️ Configuration

See `utils/config.py` for all configuration options.

Key environment variables:
```bash
MONITORING_DB_URL=sqlite:///monitoring.db
MONITORING_LOG_LEVEL=INFO
MONITORING_EXPORT_INTERVAL=60
MONITORING_RETENTION_DAYS=90
```

## 📚 Documentation

- `ARCHITECTURE.md` - Detailed system architecture
- `examples/` - Usage examples
- `dashboard/` - Dashboard documentation

## 🔐 Security

- Sensitive data filtering (API keys, credentials)
- Data encryption at rest
- Role-based access control
- Audit logging
- Rate limiting

## 📝 License

This project is part of the AI Voice Search Agent platform.

---

**For detailed architecture, see ARCHITECTURE.md**
