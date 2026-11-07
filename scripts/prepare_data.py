"""
Data Preparation & Cleaning Module for Online Retail II
Cleans raw transactions, removes cancellations, invalid prices/quantities,
handles missing customer IDs, builds baskets and interaction features,
and generates the supply-constrained operational catalogue.
Stores data in compressed CSV (.csv.gz) and SQLite for optimal storage & query efficiency.
"""

import os
import sys
import sqlite3
import numpy as np
import pandas as pd
from datetime import datetime

def clean_online_retail(raw_excel_path: str, output_dir: str, db_path: str):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Loading Online Retail II dataset from {raw_excel_path}...")
    
    sheets = ['Year 2009-2010', 'Year 2010-2011']
    df_list = []
    for sheet in sheets:
        print(f"Reading sheet '{sheet}'...")
        df_sheet = pd.read_excel(raw_excel_path, sheet_name=sheet)
        df_sheet['SourceSheet'] = sheet
        df_list.append(df_sheet)
        print(f"Loaded {len(df_sheet):,} rows from {sheet}.")

    df = pd.concat(df_list, ignore_index=True)
    total_raw_rows = len(df)
    print(f"Total raw rows: {total_raw_rows:,}")

    # Standardize column names
    df.columns = [c.strip().replace(' ', '_') for c in df.columns]

    print("\n--- Data Cleaning & Validation ---")
    
    # 1. Track exclusions: cancellations or negative quantities
    cancellations_mask = df['Invoice'].astype(str).str.startswith('C', na=False) | (df['Quantity'] <= 0)
    num_cancellations = int(cancellations_mask.sum())
    print(f"1. Cancellations / non-positive quantities: {num_cancellations:,} ({num_cancellations/total_raw_rows*100:.2f}%)")

    # 2. Non-positive or zero price
    invalid_price_mask = (df['Price'] <= 0) | (df['Price'].isna())
    num_invalid_price = int(invalid_price_mask.sum())
    print(f"2. Invalid / zero prices: {num_invalid_price:,} ({num_invalid_price/total_raw_rows*100:.2f}%)")

    # 3. Missing Customer ID
    missing_cust_mask = df['Customer_ID'].isna()
    num_missing_cust = int(missing_cust_mask.sum())
    print(f"3. Missing Customer IDs: {num_missing_cust:,} ({num_missing_cust/total_raw_rows*100:.2f}%)")

    # 4. Non-merchandise stock codes
    non_product_codes = ['POST', 'D', 'M', 'BANK CHARGES', 'PADS', 'DOT', 'CRUK', 'AMAZONFEE', 'TEST']
    non_merch_mask = df['StockCode'].astype(str).str.strip().str.upper().isin(non_product_codes)
    num_non_merch = int(non_merch_mask.sum())
    print(f"4. Non-merchandise codes: {num_non_merch:,}")

    # Filter clean dataset
    valid_mask = (~cancellations_mask) & (~invalid_price_mask) & (~missing_cust_mask) & (~non_merch_mask)
    clean_df = df[valid_mask].copy()

    # Deduplicate exact duplicate rows
    initial_clean_rows = len(clean_df)
    clean_df = clean_df.drop_duplicates(subset=['Invoice', 'StockCode', 'Customer_ID', 'InvoiceDate'])
    num_duplicates = int(initial_clean_rows - len(clean_df))
    print(f"5. Duplicate transaction rows removed: {num_duplicates:,}")

    # Type standardization
    clean_df['Customer_ID'] = clean_df['Customer_ID'].astype(int).astype(str)
    clean_df['StockCode'] = clean_df['StockCode'].astype(str).str.strip().str.upper()
    clean_df['Description'] = clean_df['Description'].astype(str).str.strip()
    clean_df['InvoiceDate'] = pd.to_datetime(clean_df['InvoiceDate'])
    clean_df['Quantity'] = clean_df['Quantity'].astype(int)
    clean_df['Price'] = clean_df['Price'].astype(float)
    clean_df['Total_Amount'] = clean_df['Quantity'] * clean_df['Price']

    # Sort chronologically
    clean_df = clean_df.sort_values(['InvoiceDate', 'Invoice'])

    print(f"\nFinal cleaned transactions count: {len(clean_df):,} rows")
    print(f"Unique Customers: {clean_df['Customer_ID'].nunique():,}")
    print(f"Unique Products (StockCodes): {clean_df['StockCode'].nunique():,}")
    print(f"Unique Invoices (Baskets): {clean_df['Invoice'].nunique():,}")
    print(f"Date Range: {clean_df['InvoiceDate'].min()} to {clean_df['InvoiceDate'].max()}")

    os.makedirs(output_dir, exist_ok=True)

    # Save to compressed CSV (.csv.gz)
    clean_gz_path = os.path.join(output_dir, 'cleaned_transactions.csv.gz')
    clean_df.to_csv(clean_gz_path, index=False, compression='gzip')
    print(f"Saved cleaned transactions to {clean_gz_path}")

    # Also save to SQLite for rapid relational queries
    conn = sqlite3.connect(db_path)
    clean_df.to_sql('cleaned_transactions', conn, if_exists='replace', index=False)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_txn_cust ON cleaned_transactions(Customer_ID)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_txn_prod ON cleaned_transactions(StockCode)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_txn_inv ON cleaned_transactions(Invoice)")
    conn.commit()
    conn.close()
    print(f"Exported cleaned transactions to SQLite table 'cleaned_transactions' in {db_path}")

    # Save Cleaning Audit Metrics
    summary_df = pd.DataFrame([
        {'metric': 'Total Raw Records', 'count': total_raw_rows},
        {'metric': 'Cancellations / Negative Qty Excluded', 'count': num_cancellations},
        {'metric': 'Zero / Negative Price Excluded', 'count': num_invalid_price},
        {'metric': 'Missing Customer ID Excluded', 'count': num_missing_cust},
        {'metric': 'Non-merchandise Codes Excluded', 'count': num_non_merch},
        {'metric': 'Duplicate Rows Dropped', 'count': num_duplicates},
        {'metric': 'Clean Valid Records Retained', 'count': len(clean_df)},
        {'metric': 'Unique Retained Customers', 'count': clean_df['Customer_ID'].nunique()},
        {'metric': 'Unique Retained Products', 'count': clean_df['StockCode'].nunique()},
        {'metric': 'Unique Retained Baskets', 'count': clean_df['Invoice'].nunique()}
    ])
    summary_path = os.path.join(output_dir, 'data_cleaning_audit.csv')
    summary_df.to_csv(summary_path, index=False)

    return clean_df


def build_baskets_and_interactions(clean_df: pd.DataFrame, output_dir: str, db_path: str):
    """
    Build basket aggregations and customer-product interaction matrices.
    """
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Building Baskets and Customer-Product Interactions...")

    # 1. Basket (Invoice) Level Table
    basket_summary = clean_df.groupby('Invoice').agg(
        customer_id=('Customer_ID', 'first'),
        invoice_date=('InvoiceDate', 'first'),
        country=('Country', 'first'),
        total_items=('Quantity', 'sum'),
        unique_items=('StockCode', 'nunique'),
        basket_revenue=('Total_Amount', 'sum'),
        product_list=('StockCode', lambda s: ",".join(sorted(set(s))))
    ).reset_index()

    baskets_gz = os.path.join(output_dir, 'baskets.csv.gz')
    basket_summary.to_csv(baskets_gz, index=False, compression='gzip')
    print(f"Created baskets dataset with {len(basket_summary):,} baskets -> {baskets_gz}")

    # 2. Customer-Product Interaction Table
    interactions = clean_df.groupby(['Customer_ID', 'StockCode']).agg(
        purchase_count=('Quantity', 'sum'),
        order_frequency=('Invoice', 'nunique'),
        total_spend=('Total_Amount', 'sum'),
        first_purchased=('InvoiceDate', 'min'),
        last_purchased=('InvoiceDate', 'max')
    ).reset_index()

    interactions_gz = os.path.join(output_dir, 'customer_interactions.csv.gz')
    interactions.to_csv(interactions_gz, index=False, compression='gzip')
    print(f"Created customer-product interactions with {len(interactions):,} pairs -> {interactions_gz}")

    # Save to SQLite
    conn = sqlite3.connect(db_path)
    basket_summary.to_sql('baskets', conn, if_exists='replace', index=False)
    interactions.to_sql('customer_interactions', conn, if_exists='replace', index=False)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_basket_cust ON baskets(customer_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_int_cust ON customer_interactions(Customer_ID)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_int_prod ON customer_interactions(StockCode)")
    conn.commit()
    conn.close()

    return basket_summary, interactions


def generate_operational_catalogue(clean_df: pd.DataFrame, output_synthetic_dir: str, db_path: str):
    """
    Creates the synthetic operational catalogue conforming strictly to Project 4 specification:
    product_id, category, unit_price, unit_cost, gross_margin, available_stock,
    reorder_point, supplier_lead_days, fulfilment_class, reward_eligible,
    max_discount_pct, data_source, last_updated_at.
    Includes explicit test cases: available stock, zero stock, low stock, low margin,
    reward-ineligible products, and unknown inventory (None/NaN).
    """
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Generating Operational Catalogue with Supply Constraints...")
    
    prod_meta = clean_df.groupby('StockCode').agg(
        description=('Description', lambda s: s.mode()[0] if not s.mode().empty else s.iloc[0]),
        unit_price=('Price', 'median'),
        total_historical_sold=('Quantity', 'sum')
    ).reset_index()

    np.random.seed(42)
    n_prods = len(prod_meta)

    categories = ['Home & Kitchen', 'Gifts & Novelties', 'Stationery & Cards', 'Seasonal & Party', 'Fashion Accessories', 'Garden & Outdoor']
    prod_meta['category'] = np.random.choice(categories, size=n_prods, p=[0.30, 0.25, 0.15, 0.12, 0.10, 0.08])

    margins = np.random.uniform(0.15, 0.65, size=n_prods)
    prod_meta['unit_cost'] = np.round(prod_meta['unit_price'] * (1 - margins), 2)
    prod_meta['gross_margin'] = np.round((prod_meta['unit_price'] - prod_meta['unit_cost']) / np.maximum(prod_meta['unit_price'], 0.01), 3)

    prod_meta['reorder_point'] = np.random.choice([10, 20, 50, 100], size=n_prods, p=[0.4, 0.3, 0.2, 0.1])
    prod_meta['supplier_lead_days'] = np.random.choice([2, 5, 7, 14, 21, 30], size=n_prods, p=[0.2, 0.3, 0.25, 0.15, 0.07, 0.03])
    prod_meta['fulfilment_class'] = np.random.choice(['Standard', 'Express', 'Heavy/Bulky', 'Fragile'], size=n_prods, p=[0.65, 0.20, 0.08, 0.07])
    prod_meta['reward_eligible'] = np.random.choice([True, False], size=n_prods, p=[0.85, 0.15])
    prod_meta['max_discount_pct'] = np.round(np.clip(prod_meta['gross_margin'] * 0.5, 0.05, 0.35), 2)

    # 70% available, 10% low stock, 10% zero stock, 10% unknown stock
    stock_status_type = np.random.choice(['available', 'low_stock', 'zero_stock', 'unknown'], size=n_prods, p=[0.70, 0.10, 0.10, 0.10])
    
    available_stocks = []
    for st in stock_status_type:
        if st == 'available':
            available_stocks.append(float(np.random.randint(50, 600)))
        elif st == 'low_stock':
            available_stocks.append(float(np.random.randint(1, 10)))
        elif st == 'zero_stock':
            available_stocks.append(0.0)
        else:
            available_stocks.append(np.nan)

    prod_meta['available_stock'] = available_stocks
    prod_meta['data_source'] = 'synthetic_catalogue_seed42'
    prod_meta['last_updated_at'] = '2026-10-30 00:00:00'
    prod_meta.rename(columns={'StockCode': 'product_id'}, inplace=True)

    # Controlled deterministic edge cases for verification:
    prod_meta.loc[0, 'available_stock'] = 250.0
    prod_meta.loc[0, 'gross_margin'] = 0.55
    prod_meta.loc[0, 'reward_eligible'] = True

    prod_meta.loc[1, 'available_stock'] = 0.0 # Out of stock
    prod_meta.loc[2, 'available_stock'] = np.nan # Unknown stock
    prod_meta.loc[3, 'gross_margin'] = 0.05 # Low margin
    prod_meta.loc[3, 'unit_cost'] = np.round(prod_meta.loc[3, 'unit_price'] * 0.95, 2)
    prod_meta.loc[4, 'reward_eligible'] = False # Reward ineligible

    os.makedirs(output_synthetic_dir, exist_ok=True)
    catalogue_csv = os.path.join(output_synthetic_dir, 'operational_catalogue.csv')
    prod_meta.to_csv(catalogue_csv, index=False)

    # Save to SQLite
    conn = sqlite3.connect(db_path)
    prod_meta.to_sql('products', conn, if_exists='replace', index=False)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_prod_cat ON products(category)")
    conn.commit()
    conn.close()

    print(f"Saved {len(prod_meta):,} catalogue products to {catalogue_csv} and SQLite table 'products'")
    return prod_meta


if __name__ == '__main__':
    raw_path = os.path.join('datasets', 'online_retail_II.xlsx')
    proc_dir = os.path.join('data', 'processed')
    synth_dir = os.path.join('data', 'synthetic')
    db_path = os.path.join('data', 'nbo_database.sqlite')
    
    clean_df = clean_online_retail(raw_path, proc_dir, db_path)
    baskets, interactions = build_baskets_and_interactions(clean_df, proc_dir, db_path)
    catalogue = generate_operational_catalogue(clean_df, synth_dir, db_path)
    print("\n[SUCCESS] Day 2 Dataset Preparation completed successfully!")
