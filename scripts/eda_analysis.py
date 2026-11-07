"""
Exploratory Data Analysis (EDA) and Visualization Generator
Generates business-relevant charts and insights:
1. Product popularity & Pareto distribution
2. Basket size & order revenue distributions
3. Supply constraint distributions (Stock Status, Margins, Categories)
4. Co-occurrence heatmap / top association rules
"""

import os
import sqlite3
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns

def run_eda(db_path: str, figures_dir: str, reports_dir: str):
    os.makedirs(figures_dir, exist_ok=True)
    os.makedirs(reports_dir, exist_ok=True)
    conn = sqlite3.connect(db_path)

    print("Running EDA analysis...")
    sns.set_theme(style="whitegrid")

    # 1. Product Popularity & Sales Volume Distribution
    prod_query = """
    SELECT StockCode, COUNT(DISTINCT Invoice) as basket_count, SUM(Quantity) as total_qty, SUM(Total_Amount) as total_revenue
    FROM cleaned_transactions
    GROUP BY StockCode
    ORDER BY basket_count DESC
    """
    prod_df = pd.read_sql(prod_query, conn)
    
    plt.figure(figsize=(10, 5))
    prod_df['cum_share'] = prod_df['basket_count'].cumsum() / prod_df['basket_count'].sum() * 100
    plt.plot(np.arange(len(prod_df)), prod_df['cum_share'], color='#1f77b4', lw=2.5)
    plt.axhline(80, color='r', linestyle='--', label='80% of Volume')
    plt.title('Pareto Chart: Cumulative Product Transaction Volume (%)', fontsize=14, fontweight='bold')
    plt.xlabel('Product Rank (StockCode)', fontsize=12)
    plt.ylabel('Cumulative % of Transactions', fontsize=12)
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(figures_dir, 'pareto_product_volume.png'), dpi=200)
    plt.close()

    # 2. Basket Size Distribution
    basket_df = pd.read_sql("SELECT total_items, basket_revenue, unique_items FROM baskets WHERE basket_revenue > 0 AND basket_revenue < 1000", conn)
    
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    sns.histplot(basket_df['unique_items'].clip(upper=40), bins=30, kde=True, ax=axes[0], color='#2ca02c')
    axes[0].set_title('Distribution of Unique Items per Basket', fontsize=12, fontweight='bold')
    axes[0].set_xlabel('Unique Items per Basket')
    
    sns.histplot(basket_df['basket_revenue'], bins=40, kde=True, ax=axes[1], color='#ff7f0e')
    axes[1].set_title('Distribution of Basket Revenue (£)', fontsize=12, fontweight='bold')
    axes[1].set_xlabel('Basket Revenue (£)')
    plt.tight_layout()
    plt.savefig(os.path.join(figures_dir, 'basket_distributions.png'), dpi=200)
    plt.close()

    # 3. Supply Constraints Breakdown from Operational Catalogue
    cat_df = pd.read_sql("SELECT * FROM products", conn)
    
    # Categorize stock
    conditions = [
        cat_df['available_stock'].isna(),
        cat_df['available_stock'] == 0,
        cat_df['available_stock'] <= cat_df['reorder_point'],
        cat_df['available_stock'] > cat_df['reorder_point']
    ]
    choices = ['Unknown Inventory (NaN)', 'Out of Stock (0)', 'Low Stock (<= Reorder)', 'Available Stock']
    cat_df['stock_status'] = np.select(conditions, choices, default='Other')

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    stock_counts = cat_df['stock_status'].value_counts()
    axes[0].pie(stock_counts, labels=stock_counts.index, autopct='%1.1f%%', colors=['#4CAF50', '#F44336', '#FF9800', '#9E9E9E'], startangle=140)
    axes[0].set_title('Inventory Availability Status Distribution', fontsize=12, fontweight='bold')

    sns.histplot(cat_df['gross_margin'], bins=25, kde=True, ax=axes[1], color='#9c27b0')
    axes[1].axvline(0.10, color='red', linestyle='--', label='Min Margin Rule (10%)')
    axes[1].set_title('Gross Margin Distribution across SKUs', fontsize=12, fontweight='bold')
    axes[1].set_xlabel('Gross Profit Margin')
    axes[1].legend()
    plt.tight_layout()
    plt.savefig(os.path.join(figures_dir, 'supply_constraints_distribution.png'), dpi=200)
    plt.close()

    conn.close()
    print("EDA Visualizations generated in figures/ directory!")

if __name__ == '__main__':
    run_eda(
        db_path=os.path.join('data', 'nbo_database.sqlite'),
        figures_dir='figures',
        reports_dir='reports'
    )
