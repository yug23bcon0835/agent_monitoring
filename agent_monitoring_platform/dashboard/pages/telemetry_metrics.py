import streamlit as st
import plotly.express as px
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from dashboard.utils import load_data

st.set_page_config(page_title="Telemetry", page_icon="📈")

st.title("📈 Telemetry & Analytics")

data_dir = "./real_agent_output"
if not os.path.exists(data_dir):
    st.error("Data directory not found.")
    st.stop()

metrics_df, events_df = load_data(data_dir)

if metrics_df.empty:
    st.warning("No metrics data available yet.")
    st.stop()

# 1. Execution Duration Over Time
st.subheader("⏱️ Execution Duration")
fig_duration = px.line(
    metrics_df, 
    x="timestamp", 
    y="duration_ms", 
    markers=True,
    title="Agent Execution Time (ms)"
)
st.plotly_chart(fig_duration, use_container_width=True)

# 2. LLM Latency
if "llm_latency_ms" in metrics_df.columns:
    st.subheader("🧠 LLM Latency")
    fig_llm = px.bar(
        metrics_df, 
        x="timestamp", 
        y="llm_latency_ms", 
        title="LLM Response Time (ms)"
    )
    st.plotly_chart(fig_llm, use_container_width=True)

# 3. Event Distribution
if not events_df.empty:
    st.subheader("📊 Event Distribution")
    event_counts = events_df["event_type"].value_counts().reset_index()
    event_counts.columns = ["Event Type", "Count"]
    
    fig_events = px.pie(
        event_counts, 
        values="Count", 
        names="Event Type", 
        title="Types of Events Recorded",
        hole=0.4
    )
    st.plotly_chart(fig_events, use_container_width=True)