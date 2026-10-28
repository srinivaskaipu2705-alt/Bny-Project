import pandas as pd

# Load datasets
internal = pd.read_csv("data/internal_ledger.csv")
custody = pd.read_csv("data/custodian_statement.csv")

# Merge on account_id
merged = pd.merge(internal, custody, on="account_id", how="outer")

# Identify matches vs breaks
matched = []
breaks = []

for idx, row in merged.iterrows():
  # Case 1: Account missing in either ledger
  if pd.isna(row["trade_id"]) or pd.isna(row["statement_id"]):
    row_dict = row.to_dict()
    row_dict["break_type"] = "ORPHAN_ACCOUNT_BREAK"
    row_dict["variance"] = row.get("expected_amount", 0) or row.get(
        "settled_amount", 0
    )
    breaks.append(row_dict)
  # Case 2: Amount matches exactly AND settled on the expected date
  elif (
      row["expected_amount"] == row["settled_amount"]
      and row["value_date"] == row["settled_date"]
  ):
    matched.append(row.to_dict())
  # Case 3: Discrepancy in amount or date
  else:
    row_dict = row.to_dict()
    variance = round(row["expected_amount"] - row["settled_amount"], 2)
    row_dict["variance"] = variance
    row_dict["break_type"] = "UNRECONCILED_VARIANCE"
    breaks.append(row_dict)

df_matched = pd.DataFrame(matched)
df_breaks = pd.DataFrame(breaks)

df_matched.to_csv("data/matched_records.csv", index=False)
df_breaks.to_csv("data/unresolved_breaks.csv", index=False)

print(f"Reconciliation Complete:")
print(f" - Clean Matched Records: {len(df_matched)}")
print(f" - Unresolved Breaks: {len(df_breaks)} (Exported to unresolved_breaks.csv)")