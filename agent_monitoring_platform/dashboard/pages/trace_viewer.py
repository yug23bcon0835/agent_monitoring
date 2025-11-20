import streamlit as st
import json
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from dashboard.utils import load_data

st.set_page_config(page_title="Trace Viewer", page_icon="📜", layout="wide")

st.title("📜 Trace Viewer")
st.markdown("Deep dive into individual agent execution steps.")

data_dir = "./real_agent_output"
metrics_df, events_df = load_data(data_dir)

if events_df.empty:
    st.warning("No events found.")
    st.stop()

# Filter Controls
col1, col2 = st.columns(2)
with col1:
    selected_type = st.multiselect(
        "Filter by Event Type", 
        options=events_df["event_type"].unique(),
        default=events_df["event_type"].unique()
    )
with col2:
    search_term = st.text_input("Search Messages/Data", "")

# Apply Filters
filtered_df = events_df[events_df["event_type"].isin(selected_type)]

if search_term:
    # Search in message or data column
    filtered_df = filtered_df[
        filtered_df["message"].str.contains(search_term, case=False, na=False) |
        filtered_df["data"].astype(str).str.contains(search_term, case=False, na=False)
    ]

st.divider()

# Display Events Timeline
for index, row in filtered_df.iterrows():
    # Color code based on severity
    color = "blue"
    icon = "ℹ️"
    if row["severity"] == "error":
        color = "red"
        icon = "❌"
    elif "start" in str(row["event_type"]).lower():
        color = "green"
        icon = "🚀"
    elif "end" in str(row["event_type"]).lower():
        color = "orange"
        icon = "🏁"

    with st.expander(f"{icon} [{row['timestamp'].strftime('%H:%M:%S')}] {row['event_type']}: {row['message']}"):
        st.write(f"**ID:** `{row['event_id']}`")
        st.write(f"**Source:** `{row['source']}`")
        if row["data"]:
            st.json(row["data"])