"""
Product Feature Engineering Utilities.
Extracts product-level historical popularity and pricing statistics.
"""

from typing import Dict, Any, List
import pandas as pd


def compute_product_catalog_features(
    transactions_df: pd.DataFrame,
    products_df: pd.DataFrame,
    cutoff_date: str,
) -> pd.DataFrame:
    """
    Computes product historical popularity metrics strictly before cutoff_date.
    """
    cutoff_dt = pd.to_datetime(cutoff_date)
    hist_txns = transactions_df[transactions_df["transaction_date"] < cutoff_dt]

    if hist_txns.empty:
        p_feats = products_df.copy()
        p_feats["hist_product_popularity"] = p_feats["product_popularity"]
        return p_feats

    prod_agg = hist_txns.groupby("product_id").agg(
        hist_orders=("transaction_id", "nunique"),
    ).reset_index()

    max_hist = prod_agg["hist_orders"].max() if not prod_agg.empty else 1.0
    prod_agg["hist_product_popularity"] = prod_agg["hist_orders"] / max(1.0, max_hist)

    p_feats = products_df.merge(prod_agg[["product_id", "hist_product_popularity"]], on="product_id", how="left")
    p_feats["hist_product_popularity"] = p_feats["hist_product_popularity"].fillna(0.0)

    return p_feats
