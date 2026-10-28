import os
import pandas as pd

# Load reconciliation & triage datasets
matched_path = "data/matched_records.csv"
triaged_path = "data/gemini_triaged_exceptions.csv"

if not os.path.exists(matched_path) or not os.path.exists(triaged_path):
    print("Missing input datasets. Ensure reconcile.py and gemini_triage_agent.py have been executed.")
    exit()

df_matched = pd.read_csv(matched_path)
df_triaged = pd.read_csv(triaged_path)

# 1. Volume & Straight-Through Processing (STP) Metrics
total_matched = len(df_matched)
total_breaks = len(df_triaged)
total_transactions = total_matched + total_breaks

auto_resolved = len(df_triaged[df_triaged["operational_status"] == "STRAIGHT_THROUGH_AUTO_RESOLVED"])
human_review = len(df_triaged[df_triaged["operational_status"].isin(["QUEUE_FOR_STANDARD_REVIEW", "ESCALATE_TO_SENIOR_ANALYST"])])

# Total automated = matched deterministically + auto-cleared by AI governance
total_automated = total_matched + auto_resolved
overall_stp_rate = (total_automated / total_transactions) * 100

# 2. Time Savings (Assumptions: 18 min per manual break investigation, 0.5 min for auto-triage)
manual_baseline_minutes = total_breaks * 18
ai_assisted_minutes = (human_review * 5) + (auto_resolved * 0.5)
minutes_saved = manual_baseline_minutes - ai_assisted_minutes
hours_saved = minutes_saved / 60

# 3. Print Executive Scorecard
print("=" * 60)
print("      BNY MIDDLE-OFFICE AI TRIAGE OPERATIONAL SCORECARD      ")
print("=" * 60)
print(f"Total Transactions Processed    : {total_transactions}")
print(f" - Clean Deterministic Matches  : {total_matched}")
print(f" - Exceptions / Breaks Detected : {total_breaks}")
print("-" * 60)
print(f"AI Straight-Through Auto-Cleared: {auto_resolved}")
print(f"Sent to Human-in-the-Loop Queue : {human_review}")
print(f"Overall Straight-Through Rate   : {overall_stp_rate:.1f}%")
print("-" * 60)
print("Breakdown by Root Cause Category:")
for cat, count in df_triaged["ai_category"].value_counts().items():
    print(f" • {cat:<24}: {count}")
print("-" * 60)
print(f"Estimated Analyst Time Saved    : {hours_saved:.2f} hours (per batch)")
print("=" * 60)