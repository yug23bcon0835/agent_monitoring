import os
import json
import glob
import pandas as pd

from sessions import SessionManager


def load_data(data_dir):
    """
    Reads all JSON files from the directory and converts them into Pandas DataFrames.
    Returns: (metrics_df, events_df)
    """
    # 1. Load Metrics (The Scores)
    metric_files = glob.glob(os.path.join(data_dir, "metrics_*.json"))
    metrics_data = []

    for fpath in metric_files:
        try:
            with open(fpath, 'r') as f:
                data = json.load(f)
                timestamp = data.get("timestamp")
                metrics = data.get("metrics", {})

                # Extract key metrics if they exist
                row = {"timestamp": timestamp, "file": os.path.basename(fpath)}

                if "agent_execution_duration" in metrics:
                    values = metrics["agent_execution_duration"].get("values", [])
                    if values:
                        vals = [v['value'] for v in values]
                        row["duration_ms"] = sum(vals) / len(vals)

                if "llm_latency_ms" in metrics:
                    values = metrics["llm_latency_ms"].get("values", [])
                    if values:
                        vals = [v['value'] for v in values]
                        row["llm_latency_ms"] = sum(vals) / len(vals)

                if "agent_success_rate" in metrics:
                    row["success_count"] = metrics["agent_success_rate"].get("total", 0)

                metrics_data.append(row)
        except Exception as e:
            print(f"Error loading {fpath}: {e}")

    metrics_df = pd.DataFrame(metrics_data)
    if not metrics_df.empty:
        metrics_df["timestamp"] = pd.to_datetime(metrics_df["timestamp"])
        metrics_df = metrics_df.sort_values("timestamp")

    # 2. Load Events
    event_files = glob.glob(os.path.join(data_dir, "events_*.json"))
    events_data = []

    for fpath in event_files:
        try:
            with open(fpath, 'r') as f:
                data = json.load(f)
                for event in data.get("events", []):
                    trace_id = event.get("context", {}).get("trace_id") or event.get("data", {}).get("trace_id")
                    event["trace_id"] = trace_id
                    events_data.append(event)
        except Exception as e:
            print(f"Error loading {fpath}: {e}")

    events_df = pd.DataFrame(events_data)
    if not events_df.empty:
        events_df["timestamp"] = pd.to_datetime(events_df["timestamp"])
        events_df = events_df.sort_values("timestamp")

    return metrics_df, events_df


def load_session_runs(data_dir: str):
    """Load persisted session runs for cross-session analysis."""
    storage_dir = os.path.join(data_dir, "sessions")
    manager = SessionManager(storage_dir=storage_dir)
    sessions = manager.list_sessions()

    rows = []
    for session in sessions:
        for run in session.runs:
            duration = run.duration_ms()
            if duration is None and run.metrics:
                duration = run.metrics.get("duration_ms")

            rows.append(
                {
                    "session_id": session.session_id,
                    "session_name": session.name,
                    "session_status": session.status,
                    "agent_id": session.agent_id,
                    "run_id": run.run_id,
                    "run_status": run.status,
                    "model": run.model or "unknown",
                    "provider": run.provider or "n/a",
                    "started_at": run.started_at,
                    "completed_at": run.completed_at,
                    "duration_ms": duration,
                    "error": run.error,
                    "tags": run.tags,
                    "metrics": run.metrics,
                }
            )

    runs_df = pd.DataFrame(rows)
    if not runs_df.empty:
        runs_df["started_at"] = pd.to_datetime(runs_df["started_at"])
        runs_df["completed_at"] = pd.to_datetime(runs_df["completed_at"])
        runs_df = runs_df.sort_values("completed_at", ascending=False)

    summary = manager.get_cross_session_summary()
    return runs_df, summary
