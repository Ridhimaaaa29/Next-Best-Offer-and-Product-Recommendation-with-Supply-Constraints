"""
DEPRECATED / LEGACY MODULE:
This module connects to a legacy SQLite database ('data/nbo_database.sqlite') and is not used
in the Day 3 / Day 4 MVP pipeline. The authoritative data store is Neon PostgreSQL.
Retained solely for historical reference.
"""


import os
import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Tuple, Dict, Any, List

class RecommenderFeatureEngine:
    def __init__(self, db_path: str = os.path.join('data', 'nbo_database.sqlite')):
        self.db_path = db_path

    def get_connection(self):
        return sqlite3.connect(self.db_path)

    def load_clean_transactions(self) -> pd.DataFrame:
        conn = self.get_connection()
        df = pd.read_sql("SELECT * FROM cleaned_transactions", conn)
        conn.close()
        df['InvoiceDate'] = pd.to_datetime(df['InvoiceDate'])
        return df

    def temporal_train_test_split(
        self, 
        df: pd.DataFrame, 
        split_date: str = '2011-09-01'
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Chronological evaluation split:
        Earlier interactions are used to construct features & train baseline.
        Later interactions are held out for out-of-time evaluation.
        Prevents lookahead target leakage.
        """
        split_dt = pd.to_datetime(split_date)
        train_df = df[df['InvoiceDate'] < split_dt].copy()
        test_df = df[df['InvoiceDate'] >= split_dt].copy()

        print(f"Temporal Split at {split_date}:")
        print(f"  Train interactions: {len(train_df):,} ({train_df['InvoiceDate'].min()} to {train_df['InvoiceDate'].max()})")
        print(f"  Test interactions:  {len(test_df):,} ({test_df['InvoiceDate'].min()} to {test_df['InvoiceDate'].max()})")
        print(f"  Train unique customers: {train_df['Customer_ID'].nunique():,}, products: {train_df['StockCode'].nunique():,}")
        print(f"  Test unique customers:  {test_df['Customer_ID'].nunique():,}, products: {test_df['StockCode'].nunique():,}")

        return train_df, test_df

    def compute_product_popularity(self, train_df: pd.DataFrame) -> pd.DataFrame:
        """
        Computes popularity features on training set only.
        Metrics: purchase_frequency, unique_buyers, total_quantity_sold.
        """
        pop = train_df.groupby('StockCode').agg(
            order_count=('Invoice', 'nunique'),
            customer_count=('Customer_ID', 'nunique'),
            total_quantity=('Quantity', 'sum'),
            total_revenue=('Total_Amount', 'sum')
        ).reset_index()

        # Score normalized between 0 and 1
        pop['popularity_score'] = np.round(
            (pop['order_count'] - pop['order_count'].min()) / 
            (pop['order_count'].max() - pop['order_count'].min() + 1e-9), 4
        )
        return pop.sort_values('popularity_score', ascending=False)

    def compute_cooccurrence_matrix(self, train_df: pd.DataFrame, min_cooccur: int = 5) -> pd.DataFrame:
        """
        Computes item-item co-occurrence and association metrics (support, confidence, lift)
        from historical training baskets.
        """
        # Get invoice - items
        basket_items = train_df[['Invoice', 'StockCode']].drop_duplicates()
        total_baskets = basket_items['Invoice'].nunique()

        # Item support
        item_counts = basket_items['StockCode'].value_counts()
        item_support = item_counts / total_baskets

        # Merge on invoice to get pairs
        merged = pd.merge(basket_items, basket_items, on='Invoice', suffixes=('_A', '_B'))
        pairs = merged[merged['StockCode_A'] != merged['StockCode_B']]

        cooccur = pairs.groupby(['StockCode_A', 'StockCode_B']).size().reset_index(name='cooccur_count')
        cooccur = cooccur[cooccur['cooccur_count'] >= min_cooccur].copy()

        # Calculate Association Metrics
        cooccur['support_AB'] = cooccur['cooccur_count'] / total_baskets
        cooccur['support_A'] = cooccur['StockCode_A'].map(item_support)
        cooccur['support_B'] = cooccur['StockCode_B'].map(item_support)
        cooccur['confidence'] = np.round(cooccur['support_AB'] / cooccur['support_A'], 4)
        cooccur['lift'] = np.round(cooccur['confidence'] / cooccur['support_B'], 4)

        return cooccur.sort_values('lift', ascending=False)
