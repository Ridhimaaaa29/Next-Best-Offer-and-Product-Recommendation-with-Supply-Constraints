import pandas as pd, os, math, json
base = r"f:/Next-Best-Offer-and-Product-Recommendation-with-Supply-Constraints"
op_path = os.path.join(base, 'data/synthetic/operational_catalogue.csv')
op = pd.read_csv(op_path)
updates = []
for idx, row in op.iterrows():
    price = row['unit_price']
    cost = row['unit_cost']
    if pd.isna(price) or pd.isna(cost) or price == 0:
        continue
    # ensure cost <= price
    if cost > price:
        new_cost = price * 0.9
        op.at[idx, 'unit_cost'] = round(new_cost, 2)
        cost = new_cost
        updates.append({'product_id': row['product_id'], 'fix': 'cost>price', 'new_cost': new_cost})
    # compute margin
    calc_margin = round((price - cost) / price, 3)
    if round(row['gross_margin_pct'], 3) != calc_margin:
        op.at[idx, 'gross_margin_pct'] = calc_margin
        updates.append({'product_id': row['product_id'], 'fix': 'margin', 'new_margin': calc_margin})
# write back
op.to_csv(op_path, index=False)
print('Updates applied:', json.dumps(updates, indent=2))
