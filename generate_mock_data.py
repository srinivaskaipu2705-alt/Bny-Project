import os
import pandas as pd

# Create data directory
os.makedirs("data", exist_ok=True)

# 1. Internal General Ledger (what the firm expects)
internal_ledger_data = [
    {
        "trade_id": "TRD-1001",
        "account_id": "ACC-8821",
        "value_date": "2026-10-20",
        "expected_amount": 150000.00,
        "currency": "USD",
        "counterparty": "JPMorgan Chase",
    },
    {
        "trade_id": "TRD-1002",
        "account_id": "ACC-8822",
        "value_date": "2026-10-21",
        "expected_amount": 75400.00,
        "currency": "USD",
        "counterparty": "Citigroup",
    },
    {
        "trade_id": "TRD-1003",
        "account_id": "ACC-8823",
        "value_date": "2026-10-21",
        "expected_amount": 22000.00,
        "currency": "USD",
        "counterparty": "Goldman Sachs",
    },
    {
        "trade_id": "TRD-1004",
        "account_id": "ACC-8824",
        "value_date": "2026-10-22",
        "expected_amount": 540000.00,
        "currency": "USD",
        "counterparty": "Morgan Stanley",
    },
    {
        "trade_id": "TRD-1005",
        "account_id": "ACC-8825",
        "value_date": "2026-10-22",
        "expected_amount": 18200.00,
        "currency": "USD",
        "counterparty": "Barclays",
    },
]

# 2. Custodian / Bank Statement (what settled at the clearing house)
custodian_statement_data = [
    {
        "statement_id": "CUST-901",
        "account_id": "ACC-8821",
        "settled_date": "2026-10-20",
        "settled_amount": 150000.00,
        "memo": "SETTLEMENT JPM TRD-1001 FULL",
    },  # Exact Match
    {
        "statement_id": "CUST-902",
        "account_id": "ACC-8822",
        "settled_date": "2026-10-21",
        "settled_amount": 75365.00,
        "memo": "CITI WIRE DEDUCT CABLE FEE $35.00 REF-1002",
    },  # Break 1: Fee deduction
    {
        "statement_id": "CUST-903",
        "account_id": "ACC-8823",
        "settled_date": "2026-10-23",
        "settled_amount": 22000.00,
        "memo": "VALUE DATE ADJ +2 DAYS GS TRD-1003",
    },  # Break 2: Timing/Settlement delay
    {
        "statement_id": "CUST-904",
        "account_id": "ACC-8824",
        "settled_date": "2026-10-22",
        "settled_amount": 530000.00,
        "memo": "PARTIAL DRAWDOWN MS ACCT 8824 REQ AMEND",
    },  # Break 3: Significant partial payment / contract break
    {
        "statement_id": "CUST-905",
        "account_id": "ACC-9999",
        "settled_date": "2026-10-22",
        "settled_amount": 18200.00,
        "memo": "INVALID SSI ROUTED TO UNCLAIMED SUSPENSE",
    },  # Break 4: SSI Routing error
]

df_internal = pd.DataFrame(internal_ledger_data)
df_custodian = pd.DataFrame(custodian_statement_data)

df_internal.to_csv("data/internal_ledger.csv", index=False)
df_custodian.to_csv("data/custodian_statement.csv", index=False)

print("Dataset generated successfully in the 'data/' folder!")