"""
Comprehensive Standalone Synthetic Data Generator for Next-Best-Offer (NBO) MVP
Generates a 100% self-contained, internally coherent synthetic e-commerce and supply-chain ecosystem:
1. customers.csv
2. products.csv
3. transactions.csv
4. baskets.csv
5. customer_product_interactions.csv
6. operational_catalogue.csv
7. policy_rules.csv

Does NOT depend on real datasets. Includes realistic customer preference archetypes,
complementary co-purchase bundles, popularity skews, and all operational constraint edge cases.
"""

import os
import random
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

def generate_synthetic_ecosystem(output_dir: str = os.path.join('data', 'synthetic')):
    os.makedirs(output_dir, exist_ok=True)
    np.random.seed(42)
    random.seed(42)

    print("Generating comprehensive synthetic ecosystem...")

    # ==========================================
    # 1. DEFINE PRODUCT TAXONOMY & CATALOGUE
    # ==========================================
    categories_def = {
        'Electronics': {
            'Audio': [
                ('Wireless Noise-Cancelling Headphones', 199.99, 110.00, 'AudioMax', 0.95),
                ('Bluetooth Pocket Speaker', 49.99, 22.00, 'SoundWave', 0.88),
                ('True Wireless Earbuds', 89.99, 45.00, 'AudioMax', 0.90),
                ('Hi-Res Studio Monitor Headphones', 149.99, 85.00, 'ProSound', 0.82),
            ],
            'Accessories': [
                ('Braided USB-C Fast Charging Cable', 14.99, 3.50, 'VoltTech', 0.92),
                ('Magnetic Wireless Charging Stand', 39.99, 16.00, 'VoltTech', 0.89),
                ('65W GaN Compact Wall Charger', 34.99, 14.00, 'VoltTech', 0.91),
                ('Waterproof Silicone Protective Case', 12.99, 2.80, 'ArmorGear', 0.85),
            ],
            'Wearables': [
                ('Smart Fitness Tracker Watch', 129.99, 65.00, 'FitPulse', 0.87),
                ('Replacement Breathable Sport Strap', 19.99, 4.00, 'FitPulse', 0.84),
                ('Smart Health Band with Sleep Monitor', 79.99, 38.00, 'FitPulse', 0.80),
            ]
        },
        'Coffee & Kitchen': {
            'Brewing': [
                ('Italian Espresso Machine Compact', 249.99, 140.00, 'BaristaCraft', 0.94),
                ('Precision Conical Burr Coffee Grinder', 99.99, 52.00, 'BaristaCraft', 0.91),
                ('Stainless Steel Pour-Over Kettle', 45.99, 20.00, 'BaristaCraft', 0.86),
                ('French Press Coffee Maker 1L', 29.99, 11.00, 'BrewArt', 0.89),
            ],
            'Beans & Supplies': [
                ('Artisan Single-Origin Coffee Beans 1kg', 28.99, 13.50, 'RoastMasters', 0.96),
                ('Dark Roast Espresso Blend 500g', 16.99, 7.50, 'RoastMasters', 0.93),
                ('Unbleached Cone Coffee Filters 100pk', 8.99, 2.00, 'BrewArt', 0.90),
                ('Vacuum Sealed Coffee Storage Canister', 24.99, 9.50, 'BaristaCraft', 0.85),
            ],
            'Kitchenware': [
                ('Double-Walled Thermal Travel Mug 450ml', 22.99, 7.50, 'ThermaGrip', 0.92),
                ('Silicone Non-Stick Baking Mat Set', 18.99, 5.00, 'ChefChoice', 0.83),
                ('Digital Food Scale with Timer', 26.99, 10.00, 'ChefChoice', 0.88),
            ]
        },
        'Health & Fitness': {
            'Equipment': [
                ('High-Density Non-Slip Yoga Mat', 34.99, 12.00, 'ZenFit', 0.91),
                ('Adjustable Dumbbell Set 20kg', 189.99, 115.00, 'IronCore', 0.89),
                ('Fabric Resistance Exercise Bands Set of 5', 19.99, 5.20, 'ZenFit', 0.93),
                ('High-Density Foam Muscle Roller', 24.99, 7.00, 'RecoveryPro', 0.86),
            ],
            'Supplements & Hydration': [
                ('Organic Whey Isolate Protein Powder 1kg', 44.99, 22.00, 'PureNutrition', 0.90),
                ('BCAA Recovery Electrolyte Powder 500g', 29.99, 12.50, 'PureNutrition', 0.87),
                ('Insulated Stainless Steel Shaker Bottle 750ml', 18.99, 5.50, 'ZenFit', 0.91),
                ('Daily Multivitamin Complex 90 Caps', 21.99, 8.00, 'PureNutrition', 0.85),
            ]
        },
        'Home & Living': {
            'Bed & Bath': [
                ('100% Organic Egyptian Cotton Sheet Set Queen', 119.99, 58.00, 'Loom & Thread', 0.93),
                ('Memory Foam Ergonomic Contour Pillow', 49.99, 21.00, 'RestWell', 0.91),
                ('Plush Turkish Bath Towel Set 4-Piece', 59.99, 26.00, 'Loom & Thread', 0.88),
            ],
            'Organization': [
                ('Modular Fabric Closet Organizer Cubes 6pk', 27.99, 9.00, 'TidySpace', 0.86),
                ('Airtight Food Storage Containers 10pk', 39.99, 15.00, 'TidySpace', 0.92),
                ('Bamboo Desktop Cable & Device Organizer', 25.99, 9.50, 'TidySpace', 0.85),
            ]
        },
        'Beauty & Skincare': {
            'Skincare': [
                ('Hydrating Hyaluronic Acid Serum 50ml', 32.99, 11.00, 'GlowLab', 0.94),
                ('Gentle Foaming Facial Cleanser 200ml', 21.99, 6.50, 'GlowLab', 0.91),
                ('SPF 50 Mineral Daily Sunscreen 100ml', 24.99, 8.00, 'PureShield', 0.93),
                ('Nourishing Overnight Ceramide Cream 60g', 38.99, 13.50, 'GlowLab', 0.89),
            ],
            'Tools': [
                ('Rose Quartz Facial Roller & Gua Sha Set', 19.99, 5.00, 'GlowLab', 0.88),
                ('Sonic Deep Cleansing Face Brush', 54.99, 22.00, 'DermaSonic', 0.86),
            ]
        }
    }

    # Flatten product records
    products_list = []
    p_id = 1
    for cat, subcats in categories_def.items():
        for subcat, prods in subcats.items():
            for name, price, cost, brand, pop in prods:
                prod_id = f"PROD_{p_id:04d}"
                rating = round(random.uniform(3.8, 4.9), 1)
                products_list.append({
                    'product_id': prod_id,
                    'product_name': name,
                    'category': cat,
                    'subcategory': subcat,
                    'brand': brand,
                    'unit_price': price,
                    'unit_cost': cost,
                    'product_rating': rating,
                    'product_popularity': pop,
                    'product_status': 'active'
                })
                p_id += 1

    # Add 10 additional specific test & constraint validation products
    additional_test_prods = [
        ('Limited Edition Gold Wireless Headphones', 'Electronics', 'Audio', 'AudioMax', 299.99, 285.00, 4.9, 0.70, 'active'), # Very low margin (5%)
        ('Legacy 30-Pin Charging Cable Vintage', 'Electronics', 'Accessories', 'VoltTech', 9.99, 4.00, 3.2, 0.20, 'discontinued'), # Inactive
        ('Commercial Grade 3-Group Espresso Bar', 'Coffee & Kitchen', 'Brewing', 'BaristaCraft', 1899.99, 1100.00, 4.9, 0.40, 'active'), # High ticket bulky
        ('Decaf Swiss Water Columbian Beans 500g', 'Coffee & Kitchen', 'Beans & Supplies', 'RoastMasters', 17.99, 7.50, 4.5, 0.75, 'active'),
        ('Pro Heavy-Duty Weightlifting Barbell 20kg', 'Health & Fitness', 'Equipment', 'IronCore', 159.99, 90.00, 4.8, 0.80, 'active'), # Heavy
        ('Collagen Peptides Powder 500g', 'Health & Fitness', 'Supplements & Hydration', 'PureNutrition', 34.99, 14.00, 4.7, 0.82, 'active'),
        ('Weighted Deep Sleep Blanket 15lbs', 'Home & Living', 'Bed & Bath', 'RestWell', 89.99, 42.00, 4.6, 0.85, 'active'),
        ('Minimalist Under-Bed Storage Bags 3pk', 'Home & Living', 'Organization', 'TidySpace', 22.99, 7.00, 4.4, 0.78, 'active'),
        ('Vitamin C 20% Brightening Serum 30ml', 'Beauty & Skincare', 'Skincare', 'GlowLab', 28.99, 9.00, 4.6, 0.88, 'active'),
        ('Organic Bamboo Reusable Makeup Remover Pads', 'Beauty & Skincare', 'Tools', 'PureShield', 14.99, 3.50, 4.5, 0.79, 'active'),
    ]

    for pname, pcat, psub, pbrand, pprice, pcost, prat, ppop, pstat in additional_test_prods:
        prod_id = f"PROD_{p_id:04d}"
        products_list.append({
            'product_id': prod_id,
            'product_name': pname,
            'category': pcat,
            'subcategory': psub,
            'brand': pbrand,
            'unit_price': pprice,
            'unit_cost': pcost,
            'product_rating': prat,
            'product_popularity': ppop,
            'product_status': pstat
        })
        p_id += 1

    products_df = pd.DataFrame(products_list)
    products_csv = os.path.join(output_dir, 'products.csv')
    products_df.to_csv(products_csv, index=False)
    print(f"1. Saved {len(products_df)} products -> {products_csv}")

    # Explicit Complementary Bundles for Realistic Co-purchasing / Baskets:
    # E.g. Espresso Machine + Grinder + Beans + Filters
    # Headphones + Charging Cable + Case
    # Yoga Mat + Resistance Bands + Shaker Bottle
    complementary_bundles = [
        ['PROD_0012', 'PROD_0013', 'PROD_0016', 'PROD_0018'], # Espresso Machine, Grinder, Beans 1kg, Filters
        ['PROD_0001', 'PROD_0005', 'PROD_0008'],             # Wireless Headphones, USB-C Cable, Case
        ['PROD_0023', 'PROD_0025', 'PROD_0029'],             # Yoga Mat, Resistance Bands, Shaker Bottle
        ['PROD_0030', 'PROD_0032'],                         # Protein Powder, Shaker Bottle
        ['PROD_0033', 'PROD_0034', 'PROD_0035'],             # Ceramide Cream, Hyaluronic Serum, Cleanser
        ['PROD_0009', 'PROD_0010'],                         # Fitness Watch, Sport Strap
        ['PROD_0026', 'PROD_0040'],                         # Dumbbell Set, Barbell
    ]

    # ==========================================
    # 2. GENERATE CUSTOMERS WITH ARCHETYPES
    # ==========================================
    num_customers = 500
    segments = ['High-Value Enthusiast', 'Tech & Gadget Aficionado', 'Health & Wellness Regular', 'Casual Budget Shopper', 'Occasional Gifter']
    tiers = ['Bronze', 'Silver', 'Gold', 'Platinum']
    locations = ['New York, NY', 'San Francisco, CA', 'Austin, TX', 'Chicago, IL', 'Seattle, WA', 'Miami, FL', 'Boston, MA', 'Denver, CO']
    age_groups = ['18-24', '25-34', '35-44', '45-54', '55+']

    customers_list = []
    customer_pref_map = {}

    for i in range(1, num_customers + 1):
        cid = f"CUST_{i:04d}"
        seg = random.choices(segments, weights=[0.15, 0.25, 0.25, 0.25, 0.10])[0]
        age = random.choices(age_groups, weights=[0.15, 0.40, 0.25, 0.15, 0.05])[0]
        loc = random.choice(locations)

        # Segment-specific attributes
        if seg == 'High-Value Enthusiast':
            tier = random.choices(['Gold', 'Platinum'], weights=[0.4, 0.6])[0]
            pts = random.randint(3000, 15000)
            pref_cat = random.choice(['Coffee & Kitchen', 'Electronics', 'Home & Living'])
            stat = 'active'
        elif seg == 'Tech & Gadget Aficionado':
            tier = random.choices(['Bronze', 'Silver', 'Gold'], weights=[0.3, 0.5, 0.2])[0]
            pts = random.randint(500, 5000)
            pref_cat = 'Electronics'
            stat = 'active'
        elif seg == 'Health & Wellness Regular':
            tier = random.choices(['Bronze', 'Silver', 'Gold'], weights=[0.3, 0.5, 0.2])[0]
            pts = random.randint(600, 6000)
            pref_cat = 'Health & Fitness'
            stat = 'active'
        elif seg == 'Casual Budget Shopper':
            tier = random.choices(['Bronze', 'Silver'], weights=[0.8, 0.2])[0]
            pts = random.randint(50, 1200)
            pref_cat = random.choice(['Beauty & Skincare', 'Home & Living', 'Electronics'])
            stat = random.choices(['active', 'dormant'], weights=[0.85, 0.15])[0]
        else: # Occasional Gifter
            tier = 'Bronze'
            pts = random.randint(0, 500)
            pref_cat = random.choice(['Beauty & Skincare', 'Coffee & Kitchen'])
            stat = random.choices(['active', 'dormant'], weights=[0.7, 0.3])[0]

        customer_pref_map[cid] = (seg, pref_cat, tier)

        customers_list.append({
            'customer_id': cid,
            'customer_segment': seg,
            'age_group': age,
            'location': loc,
            'membership_tier': tier,
            'reward_points': pts,
            'preferred_category': pref_cat,
            'average_order_value': 0.0, # Will calculate after transactions
            'total_orders': 0,
            'total_spend': 0.0,
            'last_purchase_date': None,
            'customer_status': stat
        })

    customers_df = pd.DataFrame(customers_list)

    # ==========================================
    # 3. GENERATE REALISTIC TRANSACTIONS & BASKETS
    # ==========================================
    transactions_list = []
    baskets_list = []

    start_date = datetime(2025, 1, 1)
    end_date = datetime(2026, 10, 25)
    days_range = (end_date - start_date).days

    t_counter = 1
    b_counter = 1

    # Product pools by category
    prods_by_cat = {}
    for cat in products_df['category'].unique():
        prods_by_cat[cat] = products_df[products_df['category'] == cat]['product_id'].tolist()
    all_prods = products_df['product_id'].tolist()
    prod_dict = products_df.set_index('product_id').to_dict(orient='index')

    for cid in customers_df['customer_id']:
        seg, pref_cat, tier = customer_pref_map[cid]

        # Determine number of orders based on segment
        if seg == 'High-Value Enthusiast':
            num_orders = random.randint(8, 20)
        elif seg in ['Tech & Gadget Aficionado', 'Health & Wellness Regular']:
            num_orders = random.randint(4, 12)
        elif seg == 'Casual Budget Shopper':
            num_orders = random.randint(2, 6)
        else: # Occasional
            num_orders = random.randint(1, 3)

        # Customer order dates
        order_days = sorted(random.sample(range(days_range), num_orders))

        for o_day in order_days:
            t_date = start_date + timedelta(days=o_day, hours=random.randint(8, 21), minutes=random.randint(0, 59))
            t_id = f"TXN_{t_counter:06d}"
            b_id = f"BSK_{b_counter:06d}"
            t_counter += 1
            b_counter += 1

            # Determine basket items:
            # 40% probability of selecting an explicit complementary bundle
            # 40% probability of category-preferred items
            # 20% random discovery
            basket_prods = []
            roll = random.random()
            if roll < 0.40:
                # Pick a bundle that fits preference if available
                eligible_bundles = [b for b in complementary_bundles if prod_dict[b[0]]['category'] == pref_cat]
                if not eligible_bundles:
                    eligible_bundles = complementary_bundles
                bundle = random.choice(eligible_bundles)
                # Customer buys 2 to all items in bundle
                sub_count = random.randint(2, len(bundle))
                basket_prods = random.sample(bundle, sub_count)
            elif roll < 0.80:
                # 1 to 3 items from preferred category
                count = random.randint(1, 3)
                basket_prods = random.sample(prods_by_cat[pref_cat], min(count, len(prods_by_cat[pref_cat])))
            else:
                # 1 to 2 random items
                count = random.randint(1, 2)
                basket_prods = random.sample(all_prods, count)

            # Generate transaction & basket line items
            order_total = 0.0
            order_status = random.choices(['completed', 'returned'], weights=[0.97, 0.03])[0]
            payment = random.choices(['credit_card', 'apple_pay', 'rewards_points', 'debit_card'], weights=[0.55, 0.25, 0.12, 0.08])[0]

            for pid in basket_prods:
                p_info = prod_dict[pid]
                qty = 1 if p_info['unit_price'] > 50 else random.choices([1, 2, 3], weights=[0.8, 0.15, 0.05])[0]
                price = p_info['unit_price']
                
                # Discount based on tier
                disc_pct = 0.0
                if tier == 'Platinum':
                    disc_pct = 0.15
                elif tier == 'Gold':
                    disc_pct = 0.10
                elif tier == 'Silver':
                    disc_pct = 0.05

                line_amount = round(qty * price * (1.0 - disc_pct), 2)
                order_total += line_amount

                transactions_list.append({
                    'transaction_id': t_id,
                    'customer_id': cid,
                    'transaction_date': t_date.strftime('%Y-%m-%d %H:%M:%S'),
                    'product_id': pid,
                    'quantity': qty,
                    'unit_price': price,
                    'discount_pct': disc_pct,
                    'final_amount': line_amount,
                    'payment_method': payment,
                    'order_status': order_status
                })

                baskets_list.append({
                    'basket_id': b_id,
                    'transaction_id': t_id,
                    'customer_id': cid,
                    'product_id': pid,
                    'quantity': qty
                })

    transactions_df = pd.DataFrame(transactions_list)
    baskets_df = pd.DataFrame(baskets_list)

    transactions_csv = os.path.join(output_dir, 'transactions.csv')
    baskets_csv = os.path.join(output_dir, 'baskets.csv')
    transactions_df.to_csv(transactions_csv, index=False)
    baskets_df.to_csv(baskets_csv, index=False)
    print(f"2. Saved {len(transactions_df)} transactions -> {transactions_csv}")
    print(f"3. Saved {len(baskets_df)} basket items across {baskets_df['basket_id'].nunique()} baskets -> {baskets_csv}")

    # Update Customer aggregations based on generated transactions
    valid_txns = transactions_df[transactions_df['order_status'] == 'completed']
    cust_agg = valid_txns.groupby('customer_id').agg(
        total_orders=('transaction_id', 'nunique'),
        total_spend=('final_amount', 'sum'),
        last_purchase_date=('transaction_date', 'max')
    ).reset_index()
    cust_agg['average_order_value'] = np.round(cust_agg['total_spend'] / cust_agg['total_orders'], 2)

    customers_df = customers_df.drop(columns=['total_orders', 'total_spend', 'last_purchase_date', 'average_order_value'])
    customers_df = customers_df.merge(cust_agg, on='customer_id', how='left')
    customers_df['total_orders'] = customers_df['total_orders'].fillna(0).astype(int)
    customers_df['total_spend'] = customers_df['total_spend'].fillna(0.0).round(2)
    customers_df['average_order_value'] = customers_df['average_order_value'].fillna(0.0).round(2)
    customers_df['last_purchase_date'] = customers_df['last_purchase_date'].fillna('2025-01-01 00:00:00')

    customers_csv = os.path.join(output_dir, 'customers.csv')
    customers_df.to_csv(customers_csv, index=False)
    print(f"4. Updated and saved {len(customers_df)} customers -> {customers_csv}")

    # ==========================================
    # 4. CUSTOMER_PRODUCT_INTERACTIONS.CSV
    # ==========================================
    interactions_list = []
    prod_cat_map = products_df.set_index('product_id')['category'].to_dict()
    now_dt = datetime(2026, 10, 30)

    for (cid, pid), group in valid_txns.groupby(['customer_id', 'product_id']):
        int_count = len(group)
        tot_qty = group['quantity'].sum()
        tot_spend = group['final_amount'].sum()
        last_date_str = group['transaction_date'].max()
        last_date = datetime.strptime(last_date_str, '%Y-%m-%d %H:%M:%S')

        # Recency score: decay function over days since last purchase
        days_diff = max(0, (now_dt - last_date).days)
        recency_score = round(np.exp(-days_diff / 120.0), 3)

        # Category preference score
        p_cat = prod_cat_map.get(pid, '')
        cust_pref = customer_pref_map[cid][1]
        cat_pref_score = 0.90 if p_cat == cust_pref else 0.45

        interactions_list.append({
            'customer_id': cid,
            'product_id': pid,
            'interaction_count': int_count,
            'last_interaction_date': last_date_str,
            'purchase_frequency': int_count,
            'total_quantity': int(tot_qty),
            'total_spend': round(float(tot_spend), 2),
            'category_preference_score': cat_pref_score,
            'recency_score': recency_score
        })

    interactions_df = pd.DataFrame(interactions_list)
    interactions_csv = os.path.join(output_dir, 'customer_product_interactions.csv')
    interactions_df.to_csv(interactions_csv, index=False)
    print(f"5. Saved {len(interactions_df)} customer-product interactions -> {interactions_csv}")

    # ==========================================
    # 5. OPERATIONAL_CATALOGUE.CSV (SUPPLY CONSTRAINTS)
    # ==========================================
    # Every single operational field is explicitly synthetic and controlled.
    # Deliberate edge cases are mapped to specific SKUs to prove policy enforcement!
    suppliers = [f"SUPP_{s:03d}" for s in range(1, 9)]
    warehouses = ['WH_EAST_01', 'WH_WEST_02', 'WH_CENTRAL_01', 'WH_SOUTH_01']

    op_catalogue = []
    for idx, row in products_df.iterrows():
        pid = row['product_id']
        u_price = row['unit_price']
        u_cost = row['unit_cost']
        margin_pct = round((u_price - u_cost) / u_price, 3)

        supp_id = random.choice(suppliers)
        wh_id = random.choice(warehouses)
        lead_days = random.choice([2, 5, 7, 14, 21])
        ship_days = random.choice([1, 2, 3, 5])
        fulfil_class = 'Standard'
        if u_price > 200 or 'Machine' in row['product_name'] or 'Barbell' in row['product_name']:
            fulfil_class = 'Heavy/Bulky'
        elif 'Serum' in row['product_name'] or 'Glass' in row['product_name']:
            fulfil_class = 'Fragile'
        elif 'Express' in row['product_name'] or u_price < 20:
            fulfil_class = 'Express'

        # Default standard parameters
        stock = float(random.randint(40, 450))
        inv_status = 'available'
        reorder = random.choice([10, 20, 30])
        reward_elig = True
        prom_elig = True
        max_disc = round(min(0.35, max(0.05, margin_pct * 0.5)), 2)

        # DELIBERATE EDGE CASES FOR HARD-CONSTRAINT TESTING:
        if pid == 'PROD_0001': # Noise-Cancelling Headphones -> HIGH DEMAND, FULLY FEASIBLE
            stock = 320.0
            inv_status = 'available'
            reward_elig = True
            prom_elig = True
            margin_pct = 0.45
            u_cost = round(u_price * (1 - margin_pct), 2)
        elif pid == 'PROD_0002': # Bluetooth Speaker -> OUT OF STOCK (0 units)
            stock = 0.0
            inv_status = 'out_of_stock'
        elif pid == 'PROD_0003': # Earbuds -> UNKNOWN INVENTORY (NaN / None)
            stock = np.nan
            inv_status = 'unknown'
        elif pid == 'PROD_0004': # Studio Headphones -> LOW STOCK (3 units <= reorder 20)
            stock = 3.0
            reorder = 20
            inv_status = 'low_stock'
        elif pid == 'PROD_0007': # 65W GaN Charger -> REWARD INELIGIBLE
            stock = 150.0
            inv_status = 'available'
            reward_elig = False
        elif pid == 'PROD_0012': # Espresso Machine -> BULKY FULFILMENT, HIGH MARGIN
            stock = 85.0
            inv_status = 'available'
            fulfil_class = 'Heavy/Bulky'
            ship_days = 5
        elif pid == 'PROD_0013': # Conical Burr Grinder -> OUT OF STOCK (Complementary item out of stock test)
            stock = 0.0
            inv_status = 'out_of_stock'
        elif pid == 'PROD_0016': # Artisan Single Origin Coffee Beans -> HIGH FREQUENCY, IN STOCK
            stock = 500.0
            inv_status = 'available'
        elif pid == 'PROD_0036': # Limited Edition Gold Headphones -> LOW MARGIN VIOLATION (< 10%)
            margin_pct = 0.050
            u_cost = 285.00
            stock = 50.0
            inv_status = 'available'
            max_disc = 0.02
        elif pid == 'PROD_0037': # Discontinued SKU -> ZERO STOCK & INELIGIBLE
            stock = 0.0
            inv_status = 'out_of_stock'
            reward_elig = False
            prom_elig = False
        elif pid == 'PROD_0038': # Commercial Espresso Bar -> HIGH SHIPPING RESTRICTIONS
            fulfil_class = 'Heavy/Bulky'
            ship_days = 10
            stock = 5.0
            reorder = 5
            inv_status = 'available'

        op_catalogue.append({
            'product_id': pid,
            'available_stock': stock,
            'inventory_status': inv_status,
            'reorder_point': reorder,
            'unit_price': u_price,
            'unit_cost': u_cost,
            'gross_margin_pct': margin_pct,
            'supplier_id': supp_id,
            'supplier_lead_days': lead_days,
            'warehouse_id': wh_id,
            'fulfilment_class': fulfil_class,
            'shipping_days': ship_days,
            'reward_eligible': reward_elig,
            'max_discount_pct': max_disc,
            'promotion_eligible': prom_elig,
            'data_source': 'synthetic_operational_engine_v1',
            'last_updated_at': '2026-10-30 08:00:00',
            'data_freshness_status': 'verified_fresh'
        })

    op_catalogue_df = pd.DataFrame(op_catalogue)
    op_catalogue_csv = os.path.join(output_dir, 'operational_catalogue.csv')
    op_catalogue_df.to_csv(op_catalogue_csv, index=False)
    print(f"6. Saved {len(op_catalogue_df)} operational catalogue records -> {op_catalogue_csv}")

    # ==========================================
    # 6. POLICY_RULES.CSV
    # ==========================================
    policy_rules = [
        {
            'rule_id': 'RULE_STK_001',
            'rule_name': 'Exclude Out-of-Stock Items',
            'rule_type': 'inventory',
            'threshold': '0.0',
            'operator': '<=',
            'action': 'EXCLUDE',
            'priority': 1,
            'enabled': True,
            'description': 'Candidates with available_stock <= 0 must be excluded from actionable offers to prevent fulfillment failures.'
        },
        {
            'rule_id': 'RULE_STK_002',
            'rule_name': 'Exclude Unknown Inventory',
            'rule_type': 'inventory',
            'threshold': 'NULL',
            'operator': 'IS_NULL',
            'action': 'EXCLUDE',
            'priority': 1,
            'enabled': True,
            'description': 'Products with unverified or missing inventory status must never be assumed available; excluded by fail-safe.'
        },
        {
            'rule_id': 'RULE_MAR_001',
            'rule_name': 'Minimum Margin Threshold',
            'rule_type': 'margin',
            'threshold': '0.10',
            'operator': '<',
            'action': 'EXCLUDE',
            'priority': 2,
            'enabled': True,
            'description': 'Candidates with gross profit margin strictly below 10% (0.10) cannot support recommendation discounts.'
        },
        {
            'rule_id': 'RULE_REW_001',
            'rule_name': 'Reward Redemption Eligibility',
            'rule_type': 'reward_eligibility',
            'threshold': 'True',
            'operator': '==',
            'action': 'EXCLUDE_IF_REWARD_CONTEXT',
            'priority': 3,
            'enabled': True,
            'description': 'When customer context is reward point redemption, product must have reward_eligible == True.'
        },
        {
            'rule_id': 'RULE_FUL_001',
            'rule_name': 'Maximum Permitted Shipping Days',
            'rule_type': 'fulfilment',
            'threshold': '7',
            'operator': '<=',
            'action': 'FLAG_OR_EXCLUDE_EXPRESS',
            'priority': 4,
            'enabled': True,
            'description': 'Offers requiring standard express promise cannot have estimated shipping_days > 7.'
        },
        {
            'rule_id': 'RULE_PRO_001',
            'rule_name': 'Promotion Active Status',
            'rule_type': 'promotional',
            'threshold': 'True',
            'operator': '==',
            'action': 'EXCLUDE',
            'priority': 5,
            'enabled': True,
            'description': 'Product must be flagged promotion_eligible == True to appear in targeted campaigns.'
        },
        {
            'rule_id': 'RULE_STATUS_001',
            'rule_name': 'Exclude Discontinued Products',
            'rule_type': 'status',
            'threshold': 'active',
            'operator': '!=',
            'action': 'EXCLUDE',
            'priority': 0,
            'enabled': True,
            'description': "Products with product_status not equal to 'active' must be excluded."
        }
    ]

    policy_rules_df = pd.DataFrame(policy_rules)
    policy_rules_csv = os.path.join(output_dir, 'policy_rules.csv')
    policy_rules_df.to_csv(policy_rules_csv, index=False)
    print(f"7. Saved {len(policy_rules_df)} policy rules -> {policy_rules_csv}")

    print("\n[SUCCESS] Comprehensive Synthetic Ecosystem generated successfully!")
    return {
        'customers': customers_df,
        'products': products_df,
        'transactions': transactions_df,
        'baskets': baskets_df,
        'interactions': interactions_df,
        'operational_catalogue': op_catalogue_df,
        'policy_rules': policy_rules_df
    }

if __name__ == '__main__':
    generate_synthetic_ecosystem()
