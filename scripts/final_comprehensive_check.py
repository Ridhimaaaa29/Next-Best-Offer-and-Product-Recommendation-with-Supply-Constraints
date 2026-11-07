import pandas as pd
import re
import os
import sys

base_dir = r"f:/Next-Best-Offer-and-Product-Recommendation-with-Supply-Constraints"
p_path = os.path.join(base_dir, "data/synthetic/products.csv")
op_path = os.path.join(base_dir, "data/synthetic/operational_catalogue.csv")
pol_path = os.path.join(base_dir, "data/synthetic/policy_rules.csv")
readme_path = os.path.join(base_dir, "data/synthetic/README.md")

products = pd.read_csv(p_path)
operational = pd.read_csv(op_path)
policy = pd.read_csv(pol_path)

with open(readme_path, "r", encoding="utf-8") as f:
    readme_text = f.read()

checks = []

# 1. Product IDs exact 1-to-1 match
prod_ids = set(products["product_id"])
op_ids = set(operational["product_id"])
checks.append({
    "check": "Product IDs 1-to-1 match between products.csv and operational_catalogue.csv",
    "passed": prod_ids == op_ids and len(prod_ids) == 52,
    "details": f"products.csv: {len(prod_ids)}, operational_catalogue.csv: {len(op_ids)}"
})

# 2. Synchronized unit_price and unit_cost
merged = pd.merge(products, operational, on="product_id", suffixes=("_prod", "_op"))
price_mismatch = merged[merged["unit_price_prod"] != merged["unit_price_op"]]
cost_mismatch = merged[merged["unit_cost_prod"] != merged["unit_cost_op"]]
checks.append({
    "check": "unit_price perfectly synchronized across products.csv and operational_catalogue.csv",
    "passed": len(price_mismatch) == 0,
    "details": f"{len(price_mismatch)} mismatches"
})
checks.append({
    "check": "unit_cost perfectly synchronized across products.csv and operational_catalogue.csv",
    "passed": len(cost_mismatch) == 0,
    "details": f"{len(cost_mismatch)} mismatches"
})

# 3. Unit cost <= unit price
cost_exceeds_price = operational[operational["unit_cost"] > operational["unit_price"]]
checks.append({
    "check": "unit_cost <= unit_price for all products",
    "passed": len(cost_exceeds_price) == 0,
    "details": f"{len(cost_exceeds_price)} violations"
})

# 4. Gross margin formula correctness: (unit_price - unit_cost) / unit_price
margin_errors = []
for idx, r in operational.iterrows():
    p = r["unit_price"]
    c = r["unit_cost"]
    m = r["gross_margin_pct"]
    expected_m = round((p - c) / p, 3)
    if round(m, 3) != expected_m:
        margin_errors.append((r["product_id"], m, expected_m))
checks.append({
    "check": "gross_margin_pct matches (unit_price - unit_cost) / unit_price for all 52 products",
    "passed": len(margin_errors) == 0,
    "details": f"{len(margin_errors)} errors"
})

# 5. Policy rules count: exactly 7 rules in policy_rules.csv
actual_rule_count = len(policy)
checks.append({
    "check": "policy_rules.csv contains exactly 7 rules",
    "passed": actual_rule_count == 7,
    "details": f"Found {actual_rule_count} rules"
})

# 6. Verify 7th rule is RULE_STATUS_001 for product_status != 'active' -> EXCLUDE
rule_7 = policy.iloc[6]
rule_7_valid = (
    rule_7["rule_id"] == "RULE_STATUS_001" and
    rule_7["operator"] == "!=" and
    rule_7["action"] == "EXCLUDE" and
    "active" in str(rule_7["description"]).lower() and
    "product_status" in str(rule_7["description"]).lower()
)
checks.append({
    "check": "7th rule is RULE_STATUS_001 (product_status != active -> EXCLUDE)",
    "passed": rule_7_valid,
    "details": f"ID={rule_7['rule_id']}, Op='{rule_7['operator']}', Action='{rule_7['action']}', Desc='{rule_7['description']}'"
})

# 7. Check README directory structure mentions 7 rows for policy_rules.csv
dir_match = re.search(r"policy_rules\.csv\s+#[^\n]*\((\d+)\s+rows\)", readme_text)
dir_rows = int(dir_match.group(1)) if dir_match else None
checks.append({
    "check": "README directory structure specifies 7 rows for policy_rules.csv",
    "passed": dir_rows == 7,
    "details": f"Found '{dir_rows} rows' in directory tree"
})

# 8. Check README schema table mentions 7 rows for policy_rules.csv
table_match = re.search(r"\|\s*`policy_rules\.csv`\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|", readme_text)
table_rows = int(table_match.group(1)) if table_match else None
checks.append({
    "check": "README Table Summary & Schema Quick-Reference specifies 7 rows for policy_rules.csv",
    "passed": table_rows == 7,
    "details": f"Found '{table_rows}' rows in schema table"
})

# 9. Verify deliberate test cases in README against products.csv and operational_catalogue.csv
# PROD_0001: stock 320, margin 45%, reward_eligible True
prod_01 = operational[operational["product_id"] == "PROD_0001"].iloc[0]
prod_01_ok = (prod_01["available_stock"] == 320.0 and prod_01["gross_margin_pct"] == 0.45 and prod_01["reward_eligible"] == True)
# PROD_0002: stock 0
prod_02 = operational[operational["product_id"] == "PROD_0002"].iloc[0]
prod_02_ok = (prod_02["available_stock"] == 0.0)
# PROD_0003: stock NaN
prod_03 = operational[operational["product_id"] == "PROD_0003"].iloc[0]
prod_03_ok = pd.isna(prod_03["available_stock"])
# PROD_0004: stock 3 <= reorder 20
prod_04 = operational[operational["product_id"] == "PROD_0004"].iloc[0]
prod_04_ok = (prod_04["available_stock"] == 3.0 and prod_04["reorder_point"] == 20)
# PROD_0007: reward_eligible False
prod_07 = operational[operational["product_id"] == "PROD_0007"].iloc[0]
prod_07_ok = (prod_07["reward_eligible"] == False)
# PROD_0036: margin 0.05 < 0.10, name Bamboo Desktop Cable & Device Organizer
prod_36_op = operational[operational["product_id"] == "PROD_0036"].iloc[0]
prod_36_pr = products[products["product_id"] == "PROD_0036"].iloc[0]
prod_36_ok = (prod_36_op["gross_margin_pct"] == 0.05 and prod_36_pr["product_name"] == "Bamboo Desktop Cable & Device Organizer")
# PROD_0044: status discontinued, name Legacy 30-Pin Charging Cable Vintage, stock 420
prod_44_op = operational[operational["product_id"] == "PROD_0044"].iloc[0]
prod_44_pr = products[products["product_id"] == "PROD_0044"].iloc[0]
prod_44_ok = (prod_44_pr["product_status"] == "discontinued" and prod_44_pr["product_name"] == "Legacy 30-Pin Charging Cable Vintage" and prod_44_op["available_stock"] == 420.0)

all_test_cases_ok = all([prod_01_ok, prod_02_ok, prod_03_ok, prod_04_ok, prod_07_ok, prod_36_ok, prod_44_ok])
checks.append({
    "check": "All 7 deliberate test cases verified against products.csv & operational_catalogue.csv",
    "passed": all_test_cases_ok,
    "details": f"PROD_0001:{prod_01_ok}, PROD_0002:{prod_02_ok}, PROD_0003:{prod_03_ok}, PROD_0004:{prod_04_ok}, PROD_0007:{prod_07_ok}, PROD_0036:{prod_36_ok}, PROD_0044:{prod_44_ok}"
})

print("=" * 70)
print("FINAL CROSS-FILE CONSISTENCY VERIFICATION REPORT")
print("=" * 70)
all_passed = True
for i, c in enumerate(checks, 1):
    status = "PASSED [OK]" if c["passed"] else "FAILED [X]"
    if not c["passed"]:
        all_passed = False
    print(f"{i}. [{status}] {c['check']}")
    print(f"   Details: {c['details']}")

print("=" * 70)
if all_passed:
    print("ALL CHECKS PASSED: Synthetic data layer is 100% verified and fully ready for review!")
else:
    print("SOME CHECKS FAILED: See details above.")
print("=" * 70)
