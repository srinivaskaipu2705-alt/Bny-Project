import os
import glob
import sqlite3
import pandas as pd
from pydantic import BaseModel, Field
from typing import Optional
from google import genai
from google.genai import types
from pypdf import PdfReader

# 1. Define Strict Invoice Extraction Schema
class InvoiceExtraction(BaseModel):
    invoice_number: str = Field(description="The unique invoice ID or reference number.")
    po_number: str = Field(description="The matching Purchase Order (PO) number mentioned.")
    vendor_name: str = Field(description="Name of the billing vendor.")
    subtotal_amount: float = Field(description="Subtotal before tax.")
    tax_amount: float = Field(description="Tax amount charged.")
    total_amount: float = Field(description="Total invoice amount payable.")
    remittance_notes: Optional[str] = Field(description="Any special instructions or billing notes.")

# 2. Extract Text from PDF
def extract_pdf_text(filepath: str) -> str:
    reader = PdfReader(filepath)
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    return text

# 3. 3-Way Matching Engine (ERP Comparison)
def reconcile_invoice_against_erp(extracted: InvoiceExtraction) -> dict:
    conn = sqlite3.connect("data/erp_finance.db")
    cursor = conn.cursor()
    cursor.execute("SELECT expected_amount, status FROM purchase_orders WHERE po_number = ?", (extracted.po_number,))
    result = cursor.fetchone()
    conn.close()

    result_dict = extracted.model_dump()

    if not result:
        result_dict["audit_status"] = "REJECTED_UNKNOWN_PO"
        result_dict["discrepancy_amount"] = extracted.total_amount
        result_dict["action_required"] = "Hold payment. Request valid PO from department manager."
        return result_dict

    expected_po_amount, po_status = result
    variance = round(extracted.total_amount - expected_po_amount, 2)
    result_dict["po_expected_amount"] = expected_po_amount
    result_dict["variance"] = variance

    # Business Rules
    if variance == 0.0:
        result_dict["audit_status"] = "AUTO_APPROVED_FOR_PAYMENT"
        result_dict["action_required"] = "Direct-to-payment straight-through schedule."
    elif variance > 0:
        result_dict["audit_status"] = "PRICE_VARIANCE_FLAGGED"
        result_dict["action_required"] = f"Overbilled by ${variance:,.2f}. Route to AP Supervisor for variance approval."
    else:
        result_dict["audit_status"] = "UNDERBILLED_REQUIRES_REVIEW"
        result_dict["action_required"] = f"Billed less than PO by ${abs(variance):,.2f}. Verify partial shipment."

    return result_dict

# 4. Main IDP Pipeline
def run_idp_pipeline():
    client = genai.Client()
    pdf_files = glob.glob("invoices/*.pdf")
    
    if not pdf_files:
        print("No PDF invoices found. Run generate_idp_data.py first.")
        return

    processed_invoices = []
    print(f"Starting IDP Pipeline: Processing {len(pdf_files)} PDF Invoices...\n")

    for filepath in pdf_files:
        filename = os.path.basename(filepath)
        raw_text = extract_pdf_text(filepath)

        prompt = f"""
You are an expert Accounts Payable AI Document Analyst.
Extract all key billing entities from this raw invoice text:

\"\"\"
{raw_text}
\"\"\"
"""
        try:
            response = client.models.generate_content(
                model="gemini-3.5-flash-lite",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=InvoiceExtraction,
                ),
            )
            extracted_data: InvoiceExtraction = response.parsed
            audit_result = reconcile_invoice_against_erp(extracted_data)
            audit_result["source_file"] = filename
            processed_invoices.append(audit_result)

            print(f"Processed: {filename} | Vendor: {extracted_data.vendor_name} | Status: {audit_result['audit_status']}")

        except Exception as e:
            print(f"Error processing {filename}: {e}")

    df_out = pd.DataFrame(processed_invoices)
    output_csv = "data/idp_audit_results.csv"
    df_out.to_csv(output_csv, index=False)
    print(f"\nIDP Workflow Complete! Results exported to: {output_csv}")
    print("\nAudit Status Distribution:")
    print(df_out["audit_status"].value_counts().to_string())

if __name__ == "__main__":
    run_idp_pipeline()