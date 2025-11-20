import os
import sys

import plotly.express as px
import streamlit as st

# Add parent dir to path to import utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dashboard.utils import load_data, load_session_runs

st.set_page_config(page_title="Agent Monitoring", page_icon="🤖", layout="wide")

st.title("🤖 Agent Monitoring Platform")
st.caption("Session-aware telemetry for real agents and Groq-powered models.")

with st.sidebar:
    st.header("Workspace")
    data_dir = st.text_input("Telemetry Directory", value="./real_agent_output")
    st.caption("Point this to where metrics_*.json & events_*.json are exported.")

if not os.path.exists(data_dir):
    st.error(f"Directory not found: {data_dir}")
    st.info("Run 'python examples/run_agent.py' to generate telemetry and session data.")
    st.stop()

metrics_df, events_df = load_data(data_dir)
session_runs_df, session_summary = load_session_runs(data_dir)

session_options = ["All Sessions"]
if not session_runs_df.empty:
    session_options += sorted(session_runs_df["session_name"].unique())

selected_session = st.sidebar.selectbox("Focus Session", session_options)
filtered_runs = session_runs_df
if selected_session != "All Sessions" and not session_runs_df.empty:
    filtered_runs = session_runs_df[session_runs_df["session_name"] == selected_session]

if session_summary.get("last_run_at"):
    st.sidebar.caption(f"Last run: {session_summary['last_run_at']}")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Active Sessions", session_summary.get("active_sessions", 0))
col2.metric("Total Runs", session_summary.get("total_runs", 0))
col3.metric("Success Rate", f"{session_summary.get('success_rate', 0.0):.1f}%")
col4.metric("Avg Duration", f"{session_summary.get('avg_duration_ms', 0.0):.0f} ms")

overview_tab, sessions_tab, events_tab = st.tabs(["Overview", "Sessions", "Events"])

with overview_tab:
    st.subheader("Run Performance")
    if metrics_df.empty:
        st.info("No metrics yet. Execute an agent run to populate telemetry.")
    else:
        value_columns = [col for col in ["duration_ms", "llm_latency_ms"] if col in metrics_df.columns]
        if value_columns:
            line_chart = px.line(
                metrics_df,
                x="timestamp",
                y=value_columns,
                markers=True,
                title="Latency & LLM Performance",
            )
            st.plotly_chart(line_chart, use_container_width=True)
        else:
            st.info("Latency metrics will appear once runs have been recorded.")

    st.subheader("Recent Events")
    if events_df.empty:
        st.info("No events found.")
    else:
        events_preview = events_df.tail(10)[["timestamp", "event_type", "severity", "message"]]
        st.dataframe(events_preview, use_container_width=True)

with sessions_tab:
    st.subheader("Cross-session Run Timeline")
    if filtered_runs.empty:
        st.info("No recorded session runs yet. Run an agent with the monitoring callback to capture data.")
    else:
        timeline_df = filtered_runs.copy()
        timeline_df["end_time"] = timeline_df["completed_at"].fillna(timeline_df["started_at"])
        timeline = px.timeline(
            timeline_df,
            x_start="started_at",
            x_end="end_time",
            y="session_name",
            color="run_status",
            hover_data=["model", "provider", "duration_ms", "completed_at"],
        )
        timeline.update_yaxes(autorange="reversed")
        st.plotly_chart(timeline, use_container_width=True)

        st.markdown("### Session Runs")
        display_cols = [
            "session_name",
            "run_status",
            "model",
            "duration_ms",
            "completed_at",
            "error",
        ]
        st.dataframe(filtered_runs[display_cols], use_container_width=True)

with events_tab:
    st.subheader("Telemetry Events")
    if events_df.empty:
        st.info("Event stream is empty.")
    else:
        severities = events_df["severity"].unique().tolist()
        selected_severities = st.multiselect(
            "Severity", options=severities, default=severities, key="severity-filter"
        )
        filtered_events = events_df[events_df["severity"].isin(selected_severities)]
        event_types = filtered_events["event_type"].unique().tolist()
        selected_types = st.multiselect(
            "Event Types", options=event_types, default=event_types, key="event-type-filter"
        )
        filtered_events = filtered_events[filtered_events["event_type"].isin(selected_types)]
        st.dataframe(
            filtered_events[["timestamp", "event_type", "severity", "source", "message"]],
            use_container_width=True,
        )
