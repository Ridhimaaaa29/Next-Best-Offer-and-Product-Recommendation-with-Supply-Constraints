"""
Customer Feature Engineering Utilities.
Extracts customer-level historical metrics without forward target leakage.
"""

from typing import Dict, Any, List
import pandas as pd


def compute_customer_rfm_features(
    transactions_df: pd.DataFrame,
    customers_df: pd.DataFrame,
    cutoff_date: str,
) -> pd.DataFrame:
    """
    Computes customer-level RFM features strictly before cutoff_date.
    """
    cutoff_dt = pd.to_datetime(cutoff_date)
    hist_txns = transactions_df[transactions_df["transaction_date"] < cutoff_dt]

    if hist_txns.empty:
        c_feats = customers_df[["customer_id", "reward_points", "membership_tier", "preferred_category"]].copy()
        c_feats["hist_total_orders"] = 0
        c_feats["hist_total_spend"] = 0.0
        c_feats["hist_aov"] = 0.0
        return c_feats

    cust_agg = hist_txns.groupby("customer_id").agg(
        hist_total_orders=("transaction_id", "nunique"),
        hist_total_spend=("total_amount", "sum"),
    ).reset_index()

    cust_agg["hist_aov"] = cust_agg["hist_total_spend"] / cust_agg["hist_total_orders"].clip(lower=1)

    c_feats = customers_df.merge(cust_agg, on="customer_id", how="left")
    c_feats["hist_total_orders"] = c_feats["hist_total_orders"].fillna(0).astype(int)
    c_feats["hist_total_spend"] = c_feats["hist_total_spend"].fillna(0.0)
    c_feats["hist_aov"] = c_feats["hist_aov"].fillna(0.0)

    return c_feats
