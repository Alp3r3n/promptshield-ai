"""Streamlit dashboard for PromptShield AI."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import database  # noqa: E402  (sys.path mutation above)

st.set_page_config(
    page_title="PromptShield AI Dashboard",
    page_icon="🛡️",
    layout="wide",
)

st.title("🛡️ PromptShield AI Dashboard")
st.caption("LLM security gateway — request logs, guardrail decisions, and estimated cost.")


@st.cache_data(ttl=5)
def load_logs() -> pd.DataFrame:
    rows = database.fetch_all()
    if not rows:
        return pd.DataFrame(
            columns=[
                "id", "timestamp", "user_id", "provider", "model", "prompt",
                "status", "guardrail_reason", "input_tokens", "output_tokens",
                "estimated_cost_usd", "response",
            ]
        )
    df = pd.DataFrame(rows)
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    return df


df = load_logs()

# --- Sidebar filters ----------------------------------------------------------
st.sidebar.header("Filters")
status_options = ["allowed", "blocked", "modified", "error"]
selected_statuses = st.sidebar.multiselect(
    "Status", options=status_options, default=status_options
)
provider_values = sorted(df["provider"].dropna().unique().tolist()) if not df.empty else []
selected_providers = st.sidebar.multiselect(
    "Provider", options=provider_values, default=provider_values
)

if st.sidebar.button("Refresh"):
    load_logs.clear()
    st.rerun()

filtered = df.copy()
if not filtered.empty:
    if selected_statuses:
        filtered = filtered[filtered["status"].isin(selected_statuses)]
    if selected_providers:
        filtered = filtered[filtered["provider"].isin(selected_providers)]

# --- Top-line metrics ---------------------------------------------------------
total = len(filtered)
allowed = int((filtered["status"] == "allowed").sum()) if total else 0
blocked = int((filtered["status"] == "blocked").sum()) if total else 0
modified = int((filtered["status"] == "modified").sum()) if total else 0
errors = int((filtered["status"] == "error").sum()) if total else 0
cost_total = float(filtered["estimated_cost_usd"].sum()) if total else 0.0

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Total Requests", total)
col2.metric("Allowed", allowed)
col3.metric("Blocked", blocked)
col4.metric("Modified", modified)
col5.metric("Estimated Cost (USD)", f"${cost_total:.4f}")

st.divider()

# --- Charts -------------------------------------------------------------------
left, right = st.columns(2)

with left:
    st.subheader("Top block reasons")
    if total and blocked + modified > 0:
        unsafe = filtered[filtered["status"].isin(["blocked", "modified"])]
        reasons = (
            unsafe["guardrail_reason"]
            .fillna("")
            .replace("", pd.NA)
            .dropna()
            .value_counts()
            .head(10)
        )
        if not reasons.empty:
            st.bar_chart(reasons)
        else:
            st.info("No block reasons recorded yet.")
    else:
        st.info("No blocked or modified requests yet.")

with right:
    st.subheader("Requests by status")
    if total:
        st.bar_chart(filtered["status"].value_counts())
    else:
        st.info("No requests logged yet.")

st.divider()

# --- Recent logs --------------------------------------------------------------
st.subheader("Recent prompt logs")
if total:
    show = filtered.sort_values("timestamp", ascending=False).head(100)
    st.dataframe(
        show[
            [
                "timestamp", "user_id", "provider", "model", "status",
                "guardrail_reason", "input_tokens", "output_tokens",
                "estimated_cost_usd", "prompt", "response",
            ]
        ],
        use_container_width=True,
        hide_index=True,
    )

    csv_bytes = show.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download filtered logs (CSV)",
        data=csv_bytes,
        file_name="promptshield_logs.csv",
        mime="text/csv",
    )
else:
    st.info(
        "No logs yet. Start the API with `uvicorn app.main:app --reload` and POST a "
        "prompt to /chat, then refresh this page."
    )
