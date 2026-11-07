"""
Basket Feature Extraction Utilities.
"""

from typing import Dict, Any, List
import pandas as pd


def compute_basket_aggregates(transactions_df: pd.DataFrame) -> pd.DataFrame:
    """
    Computes basket-level summary features: basket size, unique products, total amount.
    """
    if transactions_df.empty:
        return pd.DataFrame()

    basket_agg = transactions_df.groupby("basket_id").agg(
        basket_size=("quantity", "sum"),
        unique_items=("product_id", "nunique"),
        total_basket_value=("total_amount", "sum"),
    ).reset_index()

    return basket_agg
