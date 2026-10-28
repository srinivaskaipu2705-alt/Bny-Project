import os
import pandas as pd
import plotly.express as px
import streamlit as st

# Page Configuration
st.set_page_config(
    page_title="BNY Ops - AI Process Re-Engineering Portal",
    page_icon="🏦",
    layout="wide",
)

st.title("🏦 BNY Operations: AI Transformation & Process Governance Hub")
st.caption(
    "Live demonstration of automated middle-office reconciliation and"
    " intelligent document processing (IDP)."
)

# Tabs Navigation
tab_recon, tab_idp = st.tabs([
    "📈 1. Transaction Reconciliation & Break Triage",
    "📑 2. Intelligent Document Processing (IDP & AP Matching)",
])

# ==============================================================================
# TAB 1: TRANSACTION RECONCILIATION & BREAK TRIAGE
# ==============================================================================
with tab_recon:
  st.header("Financial Transaction Break Triage Engine")
  st.markdown(
      "Automated settlement break classification using Gemini and"
      " Human-in-the-Loop (HITL) risk gates."
  )

  matched_path = "data/matched_records.csv"
  triaged_path = "data/gemini_triaged_exceptions.csv"

  if os.path.exists(matched_path) and os.path.exists(triaged_path):
    df_matched = pd.read_csv(matched_path)
    df_triaged = pd.read_csv(triaged_path)

    df_triaged["variance"] = pd.to_numeric(
        df_triaged["variance"], errors="coerce"
    ).fillna(0.0)
    df_triaged["ai_confidence"] = pd.to_numeric(
        df_triaged["ai_confidence"], errors="coerce"
    ).fillna(0.0)

    total_matched = len(df_matched)
    total_breaks = len(df_triaged)
    total_tx = total_matched + total_breaks

    auto_resolved = len(
        df_triaged[
            df_triaged["operational_status"]
            == "STRAIGHT_THROUGH_AUTO_RESOLVED"
        ]
    )
    escalated = len(
        df_triaged[
            df_triaged["operational_status"] == "ESCALATE_TO_SENIOR_ANALYST"
        ]
    )
    queued = len(
        df_triaged[
            df_triaged["operational_status"] == "QUEUE_FOR_STANDARD_REVIEW"
        ]
    )

    total_automated = total_matched + auto_resolved
    stp_rate = (total_automated / total_tx) * 100 if total_tx > 0 else 0
    manual_baseline_hrs = (total_breaks * 18) / 60
    ai_hrs = ((auto_resolved * 0.5) + ((escalated + queued) * 3)) / 60
    hrs_saved = max(0.0, manual_baseline_hrs - ai_hrs)

    # Metrics Row
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Batch Volume", f"{total_tx}")
    m2.metric("Clean Matches", f"{total_matched}")
    m3.metric("Breaks Detected", f"{total_breaks}", delta="-Requires Triage")
    m4.metric(
        "Overall STP Rate",
        f"{stp_rate:.1f}%",
        delta=f"+{((auto_resolved/total_tx)*100):.1f}% AI lift",
    )
    m5.metric("Cycle Time Saved", f"{hrs_saved:.1f} hrs")

    st.divider()

    # Visuals
    c1, c2 = st.columns(2)
    with c1:
      st.subheader("Breaks by AI Root-Cause Category")
      cat_counts = (
          df_triaged["ai_category"].value_counts().reset_index()
      )
      cat_counts.columns = ["Category", "Count"]
      fig_cat = px.bar(
          cat_counts,
          x="Category",
          y="Count",
          color="Category",
          text="Count",
          color_discrete_sequence=px.colors.qualitative.Bold,
      )
      fig_cat.update_layout(
          showlegend=False, xaxis_title="", yaxis_title="Count"
      )
      st.plotly_chart(fig_cat, use_container_width=True)

    with c2:
      st.subheader("HITL Governance Routing")
      status_counts = (
          df_triaged["operational_status"].value_counts().reset_index()
      )
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
      st.plotly_chart(fig_status, use_container_width=True)

    # Detailed Table
    st.subheader("Live Break Review Queue")
    display_cols = [
        "account_id",
        "trade_id",
        "variance",
        "ai_category",
        "ai_confidence",
        "operational_status",
        "ai_gl_action",
    ]
    st.dataframe(
        df_triaged[display_cols].style.format(
            {"variance": "${:,.2f}", "ai_confidence": "{:.0%}"}
        ),
        use_container_width=True,
    )
  else:
    st.warning("Reconciliation data not found. Run reconciliation scripts.")

# ==============================================================================
# TAB 2: INTELLIGENT DOCUMENT PROCESSING (IDP)
# ==============================================================================
with tab_idp:
  st.header("Accounts Payable IDP & Automated 3-Way Matching")
  st.markdown(
      "Automated extraction from unstructured invoice PDFs with validation"
      " against ERP Purchase Orders."
  )

  idp_path = "data/idp_audit_results.csv"

  if os.path.exists(idp_path):
    df_idp = pd.read_csv(idp_path)

    # Ensure numerics
    for col in [
        "total_amount",
        "po_expected_amount",
        "variance",
        "tax_amount",
        "subtotal_amount",
    ]:
      if col in df_idp.columns:
        df_idp[col] = pd.to_numeric(df_idp[col], errors="coerce").fillna(0.0)

    # KPI Metrics
    total_invoices = len(df_idp)
    auto_pay = len(
        df_idp[df_idp["audit_status"] == "AUTO_APPROVED_FOR_PAYMENT"]
    )
    flagged = len(
        df_idp[df_idp["audit_status"] == "PRICE_VARIANCE_FLAGGED"]
    )
    rejected = len(
        df_idp[df_idp["audit_status"] == "REJECTED_UNKNOWN_PO"]
    )

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Invoices Ingested", f"{total_invoices}")
    k2.metric(
        "Straight-Through Paid",
        f"{auto_pay}",
        delta=f"{(auto_pay/total_invoices)*100:.0f}% STP",
    )
    k3.metric("Price Variance Flagged", f"{flagged}", delta="-Requires Review")
    k4.metric("Blocked (Unknown PO)", f"{rejected}", delta="-SOX Control Gate")

    st.divider()

    # Visual Distribution
    v1, v2 = st.columns([1, 1])
    with v1:
      st.subheader("Audit Status Breakdown")
      audit_counts = df_idp["audit_status"].value_counts().reset_index()
      audit_counts.columns = ["Status", "Count"]
      fig_audit = px.pie(
          audit_counts,
          names="Status",
          values="Count",
          hole=0.4,
          color="Status",
          color_discrete_map={
              "AUTO_APPROVED_FOR_PAYMENT": "#2ECC71",
              "PRICE_VARIANCE_FLAGGED": "#F39C12",
              "REJECTED_UNKNOWN_PO": "#E74C3C",
          },
      )
      st.plotly_chart(fig_audit, use_container_width=True)

    with v2:
      st.subheader("Invoiced Amount vs. PO Authorized Amount")
      fig_bar = px.bar(
          df_idp,
          x="vendor_name",
          y=["total_amount", "po_expected_amount"],
          barmode="group",
          labels={"value": "USD Amount ($)", "variable": "Metric"},
          color_discrete_map={
              "total_amount": "#3498DB",
              "po_expected_amount": "#2ECC71",
          },
      )
      fig_bar.update_layout(xaxis_title="", legend_title="")
      st.plotly_chart(fig_bar, use_container_width=True)

    # Interactive Verification Queue
    st.subheader("Invoice Audit & Verification Table")
    idp_cols = [
        "source_file",
        "vendor_name",
        "invoice_number",
        "po_number",
        "total_amount",
        "po_expected_amount",
        "variance",
        "audit_status",
        "action_required",
    ]
    st.dataframe(
        df_idp[idp_cols].style.format({
            "total_amount": "${:,.2f}",
            "po_expected_amount": "${:,.2f}",
            "variance": "${:,.2f}",
        }),
        use_container_width=True,
    )

    # 1-Click Action Simulator
    st.markdown("### 🔍 Invoice Exception Action Console")
    selected_inv = st.selectbox(
        "Select Invoice:", options=df_idp["invoice_number"].tolist()
    )
    if selected_inv:
      inv_row = df_idp[df_idp["invoice_number"] == selected_inv].iloc[0]
      st.info(
          f"**Vendor:** {inv_row['vendor_name']} | **Status:**"
          f" `{inv_row['audit_status']}`"
      )
      st.warning(f"**Action Required:** {inv_row['action_required']}")

      b1, b2, _ = st.columns([1, 1, 3])
      with b1:
        if st.button("Authorize Variance", key="auth_var"):
          st.success(
              f"Variance override approved for {selected_inv}. Sent to payment"
              " queue."
          )
      with b2:
        if st.button("Reject & Return to Vendor", key="rej_inv"):
          st.error(
              f"Invoice {selected_inv} rejected. Notification sent to vendor."
          )
  else:
    st.warning("IDP data not found. Run idp_agent.py first.")