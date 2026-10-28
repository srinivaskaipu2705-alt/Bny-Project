import os
import time
import pandas as pd
from typing import Literal
from pydantic import BaseModel, Field
from google import genai
from google.genai import types

# ===================================================
# 1. DEFINE STRUCTURED SCHEMA (DATA CONTRACT)
# ===================================================
class BreakTriageDecision(BaseModel):
    break_category: Literal[
        "FEE_DISCREPANCY", 
        "TIMING_DIFFERENCE", 
        "PARTIAL_SETTLEMENT", 
        "SSI_ROUTING_ERROR", 
        "UNKNOWN_EXCEPTION"
    ] = Field(description="Primary classification of why the reconciliation break occurred.")
    
    root_cause_explanation: str = Field(
        description="Concise 1-sentence explanation deduced from the bank memo and trade variance."
    )
    
    suggested_gl_action: str = Field(
        description="Recommended operational action or specific General Ledger debit/credit adjustment."
    )
    
    confidence_score: float = Field(
        description="Confidence score between 0.00 and 1.00 based on memo clarity and standard banking rules."
    )
    
    risk_level: Literal["LOW", "MEDIUM", "HIGH"] = Field(
        description="Risk level determined by transaction exposure and category severity."
    )


# ===================================================
# 2. PROMPT TEMPLATES & SYSTEM INSTRUCTIONS
# ===================================================
SYSTEM_INSTRUCTION = """
You are a Senior Financial Operations & Reconciliation Analyst at a global custodian bank (BNY).
Your responsibility is to analyze transaction breaks between Internal Accounting Ledgers and Custodian Bank Statements.

Evaluation Rules:
1. Classify the root cause into one of the allowed categories:
   - FEE_DISCREPANCY: Wire fees, cable charges, transfer deductions.
   - TIMING_DIFFERENCE: Value-date rollovers, weekend settlement delays.
   - PARTIAL_SETTLEMENT: Underpayments, drawdowns, or contract discrepancies.
   - SSI_ROUTING_ERROR: Invalid standard settlement instructions, suspense accounts.
   - UNKNOWN_EXCEPTION: Insufficient details to determine root cause.
2. Formulate a specific operational GL adjustment or escalation action.
3. Be objective and assign realistic confidence scores.
"""

def build_prompt(row: dict) -> str:
    return f"""
Analyze this reconciliation break:
- Trade ID: {row.get('trade_id', 'N/A')}
- Account ID: {row.get('account_id', 'N/A')}
- Counterparty: {row.get('counterparty', 'N/A')}
- Expected Date: {row.get('value_date', 'N/A')} | Expected Amount: ${row.get('expected_amount', 0):,.2f}
- Settled Date: {row.get('settled_date', 'N/A')} | Settled Amount: ${row.get('settled_amount', 0):,.2f}
- Variance: ${row.get('variance', 0):,.2f}
- Custodian Bank Memo: "{row.get('memo', 'N/A')}"
"""

# ===================================================
# 3. HUMAN-IN-THE-LOOP (HITL) GOVERNANCE POLICY
# ===================================================
def evaluate_operational_policy(variance: float, decision: BreakTriageDecision) -> str:
    abs_variance = abs(variance)
    if decision.confidence_score >= 0.90 and decision.risk_level == "LOW" and abs_variance < 1000.0:
        return "STRAIGHT_THROUGH_AUTO_RESOLVED"
    elif decision.risk_level == "HIGH" or abs_variance >= 10000.0:
        return "ESCALATE_TO_SENIOR_ANALYST"
    else:
        return "QUEUE_FOR_STANDARD_REVIEW"

# ===================================================
# 4. EXECUTION PIPELINE WITH RETRY LOGIC
# ===================================================
def run_gemini_triage():
    input_file = "data/unresolved_breaks.csv"
    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found. Run reconcile.py first!")
        return

    client = genai.Client()
    df_breaks = pd.read_csv(input_file)
    enriched_records = []

    # Using high-throughput, low-latency Flash-Lite model
    model_name = "gemini-3.5-flash-lite"
    print(f"Connecting to Gemini ({model_name}) to triage {len(df_breaks)} breaks...\n")

    for idx, row in df_breaks.iterrows():
        variance = float(row.get("variance", 0.0)) if pd.notna(row.get("variance")) else 0.0
        prompt_text = build_prompt(row.to_dict())

        # Retry loop for 503 high-demand spikes
        max_retries = 3
        backoff_seconds = 2

        for attempt in range(max_retries):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt_text,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_INSTRUCTION,
                        response_mime_type="application/json",
                        response_schema=BreakTriageDecision,
                    ),
                )

                decision: BreakTriageDecision = response.parsed
                ops_status = evaluate_operational_policy(variance, decision)

                record = row.to_dict()
                record["ai_category"] = decision.break_category
                record["ai_root_cause"] = decision.root_cause_explanation
                record["ai_gl_action"] = decision.suggested_gl_action
                record["ai_confidence"] = decision.confidence_score
                record["ai_risk_level"] = decision.risk_level
                record["operational_status"] = ops_status
                enriched_records.append(record)

                print(f"[{idx+1}/{len(df_breaks)}] Account: {record.get('account_id')} "
                      f"| Category: {decision.break_category} "
                      f"| Status: {ops_status}")
                break  # Successful, exit retry loop

            except Exception as e:
                if "503" in str(e) and attempt < max_retries - 1:
                    print(f"Server busy (503). Retrying row {idx} in {backoff_seconds}s... (Attempt {attempt+1}/{max_retries})")
                    time.sleep(backoff_seconds)
                    backoff_seconds *= 2
                else:
                    print(f"Error processing row {idx}: {e}")
                    break

        # Gentle pause between requests to prevent rate limit spikes
        time.sleep(1)

    df_output = pd.DataFrame(enriched_records)
    output_path = "data/gemini_triaged_exceptions.csv"
    df_output.to_csv(output_path, index=False)

    print(f"\nPipeline Complete! Output saved to: {output_path}")

    if not df_output.empty and "operational_status" in df_output.columns:
        print("\nOperational Routing Summary:")
        print(df_output["operational_status"].value_counts().to_string())
    else:
        print("\nNo records were processed. Check errors above.")

if __name__ == "__main__":
    run_gemini_triage()