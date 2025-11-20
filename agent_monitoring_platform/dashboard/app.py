import streamlit as st
import os
import sys

# Add parent dir to path to import utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dashboard.utils import load_data

st.set_page_config(page_title="Agent Monitoring", page_icon="🤖", layout="wide")

st.title("🤖 Agent Monitoring Platform")
st.markdown("Welcome to your AI Agent's command center.")

# Configuration in Sidebar
st.sidebar.header("Configuration")
data_dir = st.sidebar.text_input("Data Directory", value="./real_agent_output")

if os.path.exists(data_dir):
    metrics_df, events_df = load_data(data_dir)
    
    # Top Level Metrics
    col1, col2, col3 = st.columns(3)
    
    total_runs = len(metrics_df)
    avg_duration = metrics_df["duration_ms"].mean() if not metrics_df.empty and "duration_ms" in metrics_df else 0
    total_errors = len(events_df[events_df["severity"] == "error"]) if not events_df.empty else 0

    col1.metric("Total Executions", total_runs)
    col2.metric("Avg Duration", f"{avg_duration:.2f} ms")
    col3.metric("Total Errors", total_errors, delta_color="inverse")

    st.divider()
    
    st.subheader("Recent Activity")
    if not events_df.empty:
        st.dataframe(
            events_df[["timestamp", "event_type", "message", "severity"]].tail(10),
            use_container_width=True
        )
    else:
        st.info("No events found. Run your agent to generate data!")
        
else:
    st.error(f"Directory not found: {data_dir}")
    st.info("Run 'python examples/run_real_agent.py' to generate data.")