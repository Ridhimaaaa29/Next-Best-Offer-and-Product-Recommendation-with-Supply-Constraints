import pandas as pd, os, json, re
base = r"f:/Next-Best-Offer-and-Product-Recommendation-with-Supply-Constraints"
products_path = os.path.join(base, 'data/synthetic/products.csv')
oper_path = os.path.join(base, 'data/synthetic/operational_catalogue.csv')
policy_path = os.path.join(base, 'data/synthetic/policy_rules.csv')
readme_path = os.path.join(base, 'data/synthetic/README.md')

products = pd.read_csv(products_path)
oper = pd.read_csv(oper_path)
policy = pd.read_csv(policy_path)

issues = []
# 1. policy rule count (data rows)
actual_rule_count = len(policy)
if actual_rule_count != 7:
    issues.append({'type':'policy_rule_count','actual':actual_rule_count})
# 2. README table count
readme_count = None
with open(readme_path, 'r', encoding='utf-8') as f:
    for line in f:
        if line.strip().startswith('| `policy_rules.csv`'):
            m = re.search(r'\| `policy_rules\.csv` \| (\d+) \|', line)
            if m:
                readme_count = int(m.group(1))
            break
if readme_count is None:
    issues.append({'type':'readme_policy_line_missing'})
elif readme_count != actual_rule_count:
    issues.append({'type':'readme_rule_count_mismatch','readme':readme_count,'actual':actual_rule_count})
# 3. Verify seventh rule is discontinued rule
if actual_rule_count >= 7:
    seventh = policy.iloc[6]
    if seventh['rule_id'] != 'RULE_STATUS_001' or 'product_status' not in str(seventh['description']):
        issues.append({'type':'seventh_rule_wrong','rule_id':seventh.get('rule_id')})
# 4. Discontinued product stock consistency
status_map = dict(zip(products['product_id'], products['product_status']))
for _, row in oper.iterrows():
    pid = row['product_id']
    status = status_map.get(pid)
    stock = row['available_stock']
    if status and status != 'active' and pd.notna(stock) and stock > 0:
        issues.append({'type':'discontinued_with_stock','product_id':pid,'status':status,'stock':stock})
# 5. Margin consistency
for _, row in oper.iterrows():
    price = row['unit_price']
    cost = row['unit_cost']
    if pd.isna(price) or pd.isna(cost) or price == 0:
        continue
    calc = round((price - cost) / price, 3)
    if round(row['gross_margin_pct'], 3) != calc:
        issues.append({'type':'margin_mismatch','product_id':row['product_id'],'recorded':row['gross_margin_pct'],'calc':calc})
print('ISSUES', json.dumps(issues))
