import os
import json
import glob
import pandas as pd
from datetime import datetime

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
                    # Get the values list
                    values = metrics["agent_execution_duration"].get("values", [])
                    if values:
                        # Take the average of durations in this file
                        vals = [v['value'] for v in values]
                        row["duration_ms"] = sum(vals) / len(vals)
                
                if "llm_latency_ms" in metrics:
                    values = metrics["llm_latency_ms"].get("values", [])
                    if values:
                        vals = [v['value'] for v in values]
                        row["llm_latency_ms"] = sum(vals) / len(vals)
                        
                if "agent_success_rate" in metrics:
                    # Check total count
                    row["success_count"] = metrics["agent_success_rate"].get("total", 0)

                metrics_data.append(row)
        except Exception as e:
            print(f"Error loading {fpath}: {e}")

    metrics_df = pd.DataFrame(metrics_data)
    if not metrics_df.empty:
        metrics_df["timestamp"] = pd.to_datetime(metrics_df["timestamp"])
        metrics_df = metrics_df.sort_values("timestamp")

    # 2. Load Events (The Story/Traces)
    event_files = glob.glob(os.path.join(data_dir, "events_*.json"))
    events_data = []

    for fpath in event_files:
        try:
            with open(fpath, 'r') as f:
                data = json.load(f)
                for event in data.get("events", []):
                    # Extract Trace ID from context if it exists
                    trace_id = event.get("context", {}).get("trace_id")
                    # Or from data if your bridge put it there
                    if not trace_id:
                        trace_id = event.get("data", {}).get("trace_id")
    
                    event["trace_id"] = trace_id
                    events_data.append(event)
        except Exception as e:
            print(f"Error loading {fpath}: {e}")

    events_df = pd.DataFrame(events_data)
    if not events_df.empty:
        events_df["timestamp"] = pd.to_datetime(events_df["timestamp"])
        events_df = events_df.sort_values("timestamp")

    return metrics_df, events_df