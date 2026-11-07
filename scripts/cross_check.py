import pandas as pd, json, sys
base = r"f:/Next-Best-Offer-and-Product-Recommendation-with-Supply-Constraints"
products = pd.read_csv(f"{base}/data/synthetic/products.csv")
oper = pd.read_csv(f"{base}/data/synthetic/operational_catalogue.csv")
policy = pd.read_csv(f"{base}/data/synthetic/policy_rules.csv")
issues = []
# product id consistency
prod_ids = set(products['product_id'])
oper_ids = set(oper['product_id'])
missing_in_products = oper_ids - prod_ids
if missing_in_products:
    issues.append({'type':'oper_missing_in_products', 'ids':list(missing_in_products)})
missing_in_oper = prod_ids - oper_ids
if missing_in_oper:
    issues.append({'type':'products_missing_in_oper', 'ids':list(missing_in_oper)})
# margin consistency
for _, row in oper.iterrows():
    price = row['unit_price']
    cost = row['unit_cost']
    if pd.isna(price) or pd.isna(cost) or price == 0:
        continue
    calc = round((price - cost) / price, 3)
    if round(row['gross_margin_pct'], 3) != calc:
        issues.append({'type':'margin_mismatch','product_id':row['product_id'],'recorded':row['gross_margin_pct'],'calc':calc})
# stock & status checks
for _, row in oper.iterrows():
    pid = row['product_id']
    stock = row['available_stock']
    status = products.loc[products['product_id']==pid, 'product_status'].values[0]
    if status != 'active' and row['available_stock'] > 0:
        issues.append({'type':'discontinued_with_stock','product_id':pid,'status':status,'stock':stock})
# policy rule count
rule_count = len(policy)
if rule_count != 7:
    issues.append({'type':'policy_rule_count','count':rule_count})
print('ISSUES', json.dumps(issues))
