import pandas as pd
import json

p = pd.read_csv('data/synthetic/products.csv')
op = pd.read_csv('data/synthetic/operational_catalogue.csv')
pol = pd.read_csv('data/synthetic/policy_rules.csv')

print(f"Products count: {len(p)}")
print(f"Operational count: {len(op)}")
print(f"Policy rules count: {len(pol)}")
print("\n--- POLICY RULES ---")
for idx, row in pol.iterrows():
    print(f"Rule {idx+1}: {row['rule_id']} | {row['rule_name']} | {row['threshold']} | {row['operator']} | {row['action']} | {row['description']}")

print("\n--- TEST CASE ITEMS ---")
test_items = ['PROD_0001', 'PROD_0002', 'PROD_0003', 'PROD_0004', 'PROD_0007', 'PROD_0036', 'PROD_0044']
for pid in test_items:
    prod_row = p[p['product_id'] == pid].iloc[0]
    op_row = op[op['product_id'] == pid].iloc[0]
    print(f"{pid}: name='{prod_row['product_name']}', status='{prod_row['product_status']}', stock={op_row['available_stock']}, reorder={op_row['reorder_point']}, margin={op_row['gross_margin_pct']}, reward_eligible={op_row['reward_eligible']}")
