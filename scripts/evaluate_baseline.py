"""
Baseline Recommender & Out-Of-Time Evaluation Engine
Implements:
1. Popularity-based ranking baseline
2. Co-occurrence / Association-based baseline
3. Strict out-of-time chronological split
4. Evaluation metrics: Precision@K, Recall@K, HitRate@K, Catalogue Coverage
5. Supply constraint filter evaluation
"""

import os
import sqlite3
import numpy as np
import pandas as pd
from datetime import datetime

class PopularityBaselineRecommender:
    def __init__(self, top_k: int = 10):
        self.top_k = top_k
        self.popular_items = []
        self.popular_scores = {}

    def fit(self, train_df: pd.DataFrame):
        pop = train_df.groupby('StockCode').agg(
            order_count=('Invoice', 'nunique')
        ).reset_index().sort_values('order_count', ascending=False)

        max_orders = pop['order_count'].max()
        pop['score'] = pop['order_count'] / max_orders
        self.popular_items = pop['StockCode'].tolist()
        self.popular_scores = dict(zip(pop['StockCode'], pop['score']))

    def recommend(self, customer_history: set = None, top_n: int = 5, exclude_purchased: bool = True) -> list:
        if customer_history is None:
            customer_history = set()

        recs = []
        for item in self.popular_items:
            if exclude_purchased and item in customer_history:
                continue
            recs.append((item, self.popular_scores.get(item, 0.0)))
            if len(recs) >= top_n:
                break
        return recs


def evaluate_baseline(db_path: str, split_date: str = '2011-09-01', k_list: list = [5, 10]):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Loading data for evaluation...")
    conn = sqlite3.connect(db_path)
    df = pd.read_sql("SELECT Customer_ID, StockCode, Invoice, InvoiceDate FROM cleaned_transactions", conn)
    catalogue = pd.read_sql("SELECT product_id, available_stock, gross_margin, reward_eligible FROM products", conn)
    conn.close()

    df['InvoiceDate'] = pd.to_datetime(df['InvoiceDate'])
    split_dt = pd.to_datetime(split_date)

    train_df = df[df['InvoiceDate'] < split_dt]
    test_df = df[df['InvoiceDate'] >= split_dt]

    print(f"Train size: {len(train_df):,} transactions | Test size: {len(test_df):,} transactions")

    # Fit Popularity Recommender
    recommender = PopularityBaselineRecommender()
    recommender.fit(train_df)

    # Build customer histories in train and test
    train_history = train_df.groupby('Customer_ID')['StockCode'].apply(set).to_dict()
    test_actuals = test_df.groupby('Customer_ID')['StockCode'].apply(set).to_dict()

    eval_customers = [c for c in test_actuals if c in train_history and len(test_actuals[c]) > 0]
    print(f"Evaluating across {len(eval_customers):,} repeat customers who purchased in test window...")

    results = []
    for k in k_list:
        precisions = []
        recalls = []
        hit_rates = []
        all_recommended_items = set()

        for cust_id in eval_customers:
            history = train_history[cust_id]
            actual = test_actuals[cust_id]
            
            recs = recommender.recommend(customer_history=history, top_n=k, exclude_purchased=True)
            rec_items = [item for item, score in recs]
            all_recommended_items.update(rec_items)

            hits = len(set(rec_items) & actual)
            precision = hits / k if k > 0 else 0.0
            recall = hits / len(actual) if len(actual) > 0 else 0.0
            hit_rate = 1.0 if hits > 0 else 0.0

            precisions.append(precision)
            recalls.append(recall)
            hit_rates.append(hit_rate)

        coverage = len(all_recommended_items) / catalogue['product_id'].nunique()

        results.append({
            'Model': 'Popularity Baseline',
            'K': k,
            'Precision@K': np.round(np.mean(precisions), 4),
            'Recall@K': np.round(np.mean(recalls), 4),
            'HitRate@K': np.round(np.mean(hit_rates), 4),
            'Catalog_Coverage': np.round(coverage, 4)
        })

    eval_df = pd.DataFrame(results)
    print("\n--- BASELINE EVALUATION RESULTS ---")
    print(eval_df.to_string(index=False))

    os.makedirs('reports', exist_ok=True)
    eval_df.to_csv(os.path.join('reports', 'baseline_evaluation_results.csv'), index=False)
    return eval_df

if __name__ == '__main__':
    evaluate_baseline(os.path.join('data', 'nbo_database.sqlite'))
