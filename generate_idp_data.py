import os
import sqlite3
import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

os.makedirs("invoices", exist_ok=True)
os.makedirs("data", exist_ok=True)

# 1. Create Mock ERP Purchase Orders Table (SQLite)
conn = sqlite3.connect("data/erp_finance.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS purchase_orders (
    po_number TEXT PRIMARY KEY,
    vendor_name TEXT,
    expected_amount REAL,
    status TEXT
)
""")

po_records = [
    ("PO-9001", "Bloomberg Finance L.P.", 45000.00, "APPROVED"),
    ("PO-9002", "Refinitiv US LLC", 28500.00, "APPROVED"),
    ("PO-9003", "Amazon Web Services", 12400.00, "APPROVED")
]

cursor.executemany("INSERT OR REPLACE INTO purchase_orders VALUES (?, ?, ?, ?)", po_records)
conn.commit()
conn.close()

# 2. Helper to Generate Realistic Invoice PDFs
def create_invoice_pdf(filename, invoice_no, po_no, vendor, amount, tax, total, notes):
    filepath = os.path.join("invoices", filename)
    c = canvas.Canvas(filepath, pagesize=letter)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, 750, f"INVOICE: {vendor}")
    
    c.setFont("Helvetica", 10)
    c.drawString(50, 730, f"Invoice Number: {invoice_no}")
    c.drawString(50, 715, f"Purchase Order Ref: {po_no}")
    c.drawString(50, 700, f"Date: 2026-10-25")
    
    c.line(50, 680, 550, 680)
    c.drawString(50, 660, "Description")
    c.drawString(450, 660, "Amount (USD)")
    c.line(50, 650, 550, 650)
    
    c.drawString(50, 630, f"Financial Market Data & Services ({po_no})")
    c.drawString(450, 630, f"${amount:,.2f}")
    
    c.drawString(50, 600, "Applicable State/Local Tax:")
    c.drawString(450, 600, f"${tax:,.2f}")
    
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, 570, "Total Amount Due:")
    c.drawString(450, 570, f"${total:,.2f}")
    
    c.setFont("Helvetica-Oblique", 9)
    c.drawString(50, 530, f"Remittance Note: {notes}")
    c.save()
    print(f"Generated: {filepath}")

# Generate 3 distinct test cases:
# Case 1: Clean Exact Match
create_invoice_pdf("inv_bloomberg_clean.pdf", "INV-8810", "PO-9001", "Bloomberg Finance L.P.", 42000.00, 3000.00, 45000.00, "Standard monthly data feed billing.")

# Case 2: Price Discrepancy (Billed 31,500 vs PO expected 28,500)
create_invoice_pdf("inv_refinitiv_variance.pdf", "INV-8811", "PO-9002", "Refinitiv US LLC", 29500.00, 2000.00, 31500.00, "Includes unexpected premium enterprise surcharge $3,000.")

# Case 3: Missing / Unrecognized PO
create_invoice_pdf("inv_aws_unmapped.pdf", "INV-8812", "PO-9999", "Amazon Web Services", 12000.00, 400.00, 12400.00, "Cloud infrastructure usage - PO reference pending approval.")

print("\nMock ERP Database and Invoices successfully created!")