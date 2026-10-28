import os
import pandas as pd
import plotly.express as px
import streamlit as st

# Page Configuration
st.set_page_config(
    page_title="BNY Ops - Financial Break Triage Dashboard",
    page_icon="🏦",
    layout="wide",
)

st.title("🏦 BNY Middle-Office: AI Exception Triage & Governance Dashboard")
st.caption(
    "Automated reconciliation, LLM root-cause classification, and"
    " Human-in-the-Loop (HITL) risk governance."
)

# File Paths
matched_path = "data/matched_records.csv"
triaged_path = "data/gemini_triaged_exceptions.csv"

if not os.path.exists(matched_path) or not os.path.exists(triaged_path):
  st.error(
      "Missing data files! Make sure you ran reconcile.py and"
      " gemini_triage_agent.py first."
  )
  st.stop()

# Load Datasets
df_matched = pd.read_csv(matched_path)
df_triaged = pd.read_csv(triaged_path)

# Ensure numeric columns
df_triaged["variance"] = pd.to_numeric(
    df_triaged["variance"], errors="coerce"
).fillna(0.0)
df_triaged["ai_confidence"] = pd.to_numeric(
    df_triaged["ai_confidence"], errors="coerce"
).fillna(0.0)

# Calculate High-Level Metrics
total_matched = len(df_matched)
total_breaks = len(df_triaged)
total_tx = total_matched + total_breaks

auto_resolved = len(
    df_triaged[
        df_triaged["operational_status"] == "STRAIGHT_THROUGH_AUTO_RESOLVED"
    ]
)
escalated = len(
    df_triaged[
        df_triaged["operational_status"] == "ESCALATE_TO_SENIOR_ANALYST"
    ]
)
queued = len(
    df_triaged[df_triaged["operational_status"] == "QUEUE_FOR_STANDARD_REVIEW"]
)

total_automated = total_matched + auto_resolved
stp_rate = (total_automated / total_tx) * 100 if total_tx > 0 else 0

# Time Saved Model: 18 mins per manual break vs 1 min with AI assist
manual_baseline_hrs = (total_breaks * 18) / 60
ai_hrs = ((auto_resolved * 0.5) + ((escalated + queued) * 3)) / 60
hrs_saved = max(0.0, manual_baseline_hrs - ai_hrs)

# ==========================================
# 1. EXECUTIVE KPI SUMMARY ROW
# ==========================================
col1, col2, col3, col4, col5 = st.columns(5)

col1.metric("Total Batch Transactions", f"{total_tx}")
col2.metric("Clean Matches (Deterministic)", f"{total_matched}")
col3.metric("Exceptions / Breaks", f"{total_breaks}", delta="-Requires Triage")
col4.metric(
    "Overall STP Rate",
    f"{stp_rate:.1f}%",
    delta=f"+{((auto_resolved/total_tx)*100):.1f}% AI lift",
)
col5.metric(
    "Analyst Time Saved", f"{hrs_saved:.1f} hrs", delta="Per Settlement Cycle"
)

st.divider()

# ==========================================
# 2. CHARTS: CATEGORY & GOVERNANCE STATUS
# ==========================================
chart_col1, chart_col2 = st.columns(2)

with chart_col1:
  st.subheader("📊 Breaks by AI Root-Cause Category")
  cat_counts = (
      df_triaged["ai_category"].value_counts().reset_index()
  )  # columns: ai_category, count
  cat_counts.columns = ["Category", "Count"]

  fig_cat = px.bar(
      cat_counts,
      x="Category",
      y="Count",
      color="Category",
      text="Count",
      color_discrete_sequence=px.colors.qualitative.Bold,
  )
  fig_cat.update_layout(showlegend=False, xaxis_title="", yaxis_title="Count")
  st.plotly_chart(fig_cat, use_container_width=True)

with chart_col2:
  st.subheader("🛡️ Human-in-the-Loop Routing Breakdown")
  status_counts = df_triaged["operational_status"].value_counts().reset_index()
  status_counts.columns = ["Routing Status", "Count"]

  fig_status = px.pie(
      status_counts,
      names="Routing Status",
      values="Count",
      hole=0.45,
      color="Routing Status",
      color_discrete_map={
          "STRAIGHT_THROUGH_AUTO_RESOLVED": "#2ECC71",
          "QUEUE_FOR_STANDARD_REVIEW": "#F39C12",
          "ESCALATE_TO_SENIOR_ANALYST": "#E74C3C",
      },
  )
  fig_status.update_traces(textposition="inside", textinfo="percent+label")
  st.plotly_chart(fig_status, use_container_width=True)

st.divider()

# ==========================================
# 3. INTERACTIVE HUMAN-IN-THE-LOOP EXCEPTION TRIAGE TABLE
# ==========================================
st.subheader("🔍 Operations Queue: Human-in-the-Loop Review")
st.write(
    "Analysts can inspect individual AI classifications, review model"
    " confidence scores, and verify suggested GL adjustments before posting."
)

# Filter by Operational Routing Status
status_filter = st.selectbox(
    "Filter by Status:",
    options=["ALL"] + list(df_triaged["operational_status"].unique()),
    index=0,
)

filtered_df = df_triaged.copy()
if status_filter != "ALL":
  filtered_df = filtered_df[filtered_df["operational_status"] == status_filter]

# Display Table
display_cols = [
    "account_id",
    "trade_id",
    "variance",
    "ai_category",
    "ai_confidence",
    "ai_risk_level",
    "operational_status",
    "ai_root_cause",
    "ai_gl_action",
    "memo",
]
st.dataframe(
    filtered_df[display_cols].style.format(
        {"variance": "${:,.2f}", "ai_confidence": "{:.0%}"}
    ),
    use_container_width=True,
    height=280,
)

# Detailed Exception Viewer
st.markdown("### 📝 Exception Resolution Action Card")
selected_account = st.selectbox(
    "Select Account to Action:", options=filtered_df["account_id"].tolist()
)

if selected_account:
  record = (
      filtered_df[filtered_df["account_id"] == selected_account].iloc[0].to_dict()
  )

  c1, c2, c3 = st.columns(3)
  c1.info(f"**Trade ID:** {record.get('trade_id', 'N/A')}")
  c2.warning(f"**Variance:** ${abs(float(record.get('variance', 0))):,.2f}")
  c3.success(f"**AI Confidence:** {float(record.get('ai_confidence', 0)):.0%}")

  st.write(f"**Bank Memo:** `{record.get('memo', 'N/A')}`")
  st.write(f"**Root Cause:** {record.get('ai_root_cause', 'N/A')}")
  st.write(
      f"**Recommended GL Action:** `{record.get('ai_gl_action', 'N/A')}`"
  )

  action_col1, action_col2, action_col3 = st.columns([1, 1, 4])
  with action_col1:
    if st.button("✅ Post GL Adjustment", key="approve"):
      st.success(
          f"Approved! Journal adjustment posted for account {selected_account}."
      )
  with action_col2:
    if st.button("⚠️ Escalate to Lead", key="escalate"):
      st.warning(
          f"Ticket escalated to Senior Operations Lead for {selected_account}."
      )