"""
Leakage-Safe Dataset Builder for Customer-Offer Purchase Propensity
Project: Next-Best-Offer and Product Recommendation with Supply Constraints

Enforces strict chronological separation:
- Development Window (Train + Validation):
    Feature history: transactions < 2026-01-01
    Target window:   transactions between 2026-01-01 and 2026-05-31
- Holdout Window (Untouched Final Test):
    Feature history: transactions < 2026-06-01
    Target window:   transactions between 2026-06-01 and 2026-10-24

Negative-Label Semantics:
- Y = 1: Customer purchased product in target window.
- Y = 0: Customer did NOT purchase product in target window.
- Sampling choice: 3 unpurchased products per positive purchase, sampled with fixed seed (seed=42).
  (Note: Strictly an experimental negative-sampling choice, NOT an observed real-world conversion ratio).
"""

import os
import random
import numpy as np
import pandas as pd
import psycopg
from datetime import datetime
from dotenv import load_dotenv
from typing import Tuple, Dict, Any, List

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL not found in .env")


class PropensityDatasetBuilder:
    def __init__(self, random_seed: int = 42):
        self.random_seed = random_seed

    def fetch_raw_tables(self) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """Fetch transactions, customers, and products from Neon PostgreSQL."""
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT transaction_id, customer_id, product_id, transaction_date, quantity, final_amount
                    FROM transactions
                    ORDER BY transaction_date ASC;
                """)
                txn_rows = cur.fetchall()

                cur.execute("""
                    SELECT customer_id, customer_segment, membership_tier, reward_points, preferred_category
                    FROM customers;
                """)
                cust_rows = cur.fetchall()

                cur.execute("""
                    SELECT product_id, product_name, category, subcategory, brand, unit_price, unit_cost, product_rating, product_popularity, product_status
                    FROM products;
                """)
                prod_rows = cur.fetchall()

        txn_df = pd.DataFrame(txn_rows, columns=["transaction_id", "customer_id", "product_id", "transaction_date", "quantity", "final_amount"])
        txn_df["transaction_date"] = pd.to_datetime(txn_df["transaction_date"])
        txn_df["final_amount"] = txn_df["final_amount"].astype(float)
        txn_df["quantity"] = txn_df["quantity"].astype(int)

        cust_df = pd.DataFrame(cust_rows, columns=["customer_id", "customer_segment", "membership_tier", "reward_points", "preferred_category"])
        cust_df["reward_points"] = cust_df["reward_points"].astype(int)

        prod_df = pd.DataFrame(prod_rows, columns=["product_id", "product_name", "category", "subcategory", "brand", "unit_price", "unit_cost", "product_rating", "product_popularity", "product_status"])
        for col in ["unit_price", "unit_cost", "product_rating", "product_popularity"]:
            prod_df[col] = prod_df[col].astype(float)

        return txn_df, cust_df, prod_df

    def build_features_for_cutoff(
        self,
        txn_df: pd.DataFrame,
        cust_df: pd.DataFrame,
        prod_df: pd.DataFrame,
        cutoff_date: str,
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """
        Build customer, product, and interaction features strictly using
        transactions occurring prior to `cutoff_date`.
        """
        cutoff_dt = pd.to_datetime(cutoff_date)
        hist_txn = txn_df[txn_df["transaction_date"] < cutoff_dt].copy()

        # 1. Product features as of cutoff
        prod_pop = hist_txn.groupby("product_id")["transaction_id"].nunique().reset_index()
        prod_pop.columns = ["product_id", "hist_order_count"]
        max_orders = prod_pop["hist_order_count"].max() if len(prod_pop) > 0 else 1.0

        p_feats = prod_df.copy()
        p_feats = p_feats.merge(prod_pop, on="product_id", how="left")
        p_feats["hist_order_count"] = p_feats["hist_order_count"].fillna(0)
        p_feats["hist_product_popularity"] = p_feats["hist_order_count"] / (max_orders if max_orders > 0 else 1.0)

        # 2. Customer features as of cutoff
        c_agg = hist_txn.groupby("customer_id").agg(
            hist_total_orders=("transaction_id", "nunique"),
            hist_total_spend=("final_amount", "sum"),
            hist_last_date=("transaction_date", "max"),
        ).reset_index()
        c_agg["hist_aov"] = c_agg["hist_total_spend"] / c_agg["hist_total_orders"].clip(lower=1)

        c_feats = cust_df.copy()
        c_feats = c_feats.merge(c_agg, on="customer_id", how="left")
        c_feats["hist_total_orders"] = c_feats["hist_total_orders"].fillna(0).astype(int)
        c_feats["hist_total_spend"] = c_feats["hist_total_spend"].fillna(0.0)
        c_feats["hist_aov"] = c_feats["hist_aov"].fillna(0.0)

        # 3. Customer-Product interactions as of cutoff
        cp_agg = hist_txn.groupby(["customer_id", "product_id"]).agg(
            hist_interaction_count=("transaction_id", "count"),
            hist_total_quantity=("quantity", "sum"),
            hist_total_spend=("final_amount", "sum"),
            hist_last_interaction=("transaction_date", "max"),
        ).reset_index()

        cp_agg["hist_recency_days"] = (cutoff_dt - cp_agg["hist_last_interaction"]).dt.days
        cp_agg["hist_recency_days"] = cp_agg["hist_recency_days"].fillna(365).clip(lower=0)

        return c_feats, p_feats, cp_agg

    def create_labeled_dataset(
        self,
        txn_df: pd.DataFrame,
        c_feats: pd.DataFrame,
        p_feats: pd.DataFrame,
        cp_agg: pd.DataFrame,
        target_start_date: str,
        target_end_date: str,
        negative_ratio: int = 3,
    ) -> pd.DataFrame:
        """
        Create labeled dataset for a target window.
        Y=1 for purchases in [target_start_date, target_end_date].
        Y=0 sampled at negative_ratio:1 from products unpurchased by the customer in this window.
        """
        start_dt = pd.to_datetime(target_start_date)
        end_dt = pd.to_datetime(target_end_date)

        target_txns = txn_df[
            (txn_df["transaction_date"] >= start_dt) &
            (txn_df["transaction_date"] <= end_dt)
        ].copy()

        # All available product IDs in the catalog
        all_product_ids = set(p_feats["product_id"].unique())

        # Group purchases by customer in target window
        customer_positives = target_txns.groupby("customer_id")["product_id"].apply(set).to_dict()

        rng = random.Random(self.random_seed)
        records = []

        for cust_id, bought_set in customer_positives.items():
            if not bought_set:
                continue

            # 1. Positive examples (Y = 1)
            for prod_id in bought_set:
                records.append({
                    "customer_id": cust_id,
                    "product_id": prod_id,
                    "target": 1,
                })

            # 2. Negative examples (Y = 0)
            # Products not purchased by this customer in target window
            unbought_candidates = sorted(list(all_product_ids - bought_set))
            n_neg = min(len(unbought_candidates), len(bought_set) * negative_ratio)
            sampled_negatives = rng.sample(unbought_candidates, n_neg)

            for prod_id in sampled_negatives:
                records.append({
                    "customer_id": cust_id,
                    "product_id": prod_id,
                    "target": 0,
                })

        dataset = pd.DataFrame(records)

        # Merge pre-cutoff customer features
        dataset = dataset.merge(
            c_feats[[
                "customer_id", "membership_tier", "reward_points",
                "preferred_category", "hist_total_orders", "hist_total_spend", "hist_aov"
            ]],
            on="customer_id",
            how="left"
        )

        # Merge pre-cutoff product features
        dataset = dataset.merge(
            p_feats[[
                "product_id", "category", "subcategory", "unit_price",
                "unit_cost", "product_rating", "product_popularity", "hist_product_popularity"
            ]],
            on="product_id",
            how="left"
        )

        # Rename cp_agg interaction spend to avoid collision with customer total spend
        cp_feats = cp_agg.rename(columns={"hist_total_spend": "hist_total_spend_interaction"})

        # Merge pre-cutoff customer-product interaction features
        dataset = dataset.merge(
            cp_feats[[
                "customer_id", "product_id", "hist_interaction_count",
                "hist_total_quantity", "hist_total_spend_interaction", "hist_recency_days"
            ]],
            on=["customer_id", "product_id"],
            how="left"
        )

        # Fill missing interaction features for un-interacted pairs
        dataset["hist_interaction_count"] = dataset["hist_interaction_count"].fillna(0).astype(int)
        dataset["hist_total_quantity"] = dataset["hist_total_quantity"].fillna(0).astype(int)
        dataset["hist_total_spend_interaction"] = dataset["hist_total_spend_interaction"].fillna(0.0)
        dataset["hist_recency_days"] = dataset["hist_recency_days"].fillna(365.0)

        # Compute affinity flag
        dataset["is_preferred_category"] = (dataset["preferred_category"] == dataset["category"]).astype(int)

        # Shuffle deterministically
        dataset = dataset.sample(frac=1.0, random_state=self.random_seed).reset_index(drop=True)
        return dataset

    def build_train_and_test_datasets(
        self,
        negative_ratio: int = 3,
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Builds:
        1. Training/Validation dataset (Features < 2026-01-01, Target in 2026-01-01 -> 2026-05-31)
        2. Untouched Test dataset (Features < 2026-06-01, Target in 2026-06-01 -> 2026-10-24)
        """
        txn_df, cust_df, prod_df = self.fetch_raw_tables()

        # Development Dataset
        c_feats_dev, p_feats_dev, cp_agg_dev = self.build_features_for_cutoff(
            txn_df, cust_df, prod_df, cutoff_date="2026-01-01"
        )
        dev_df = self.create_labeled_dataset(
            txn_df, c_feats_dev, p_feats_dev, cp_agg_dev,
            target_start_date="2026-01-01", target_end_date="2026-05-31",
            negative_ratio=negative_ratio
        )

        # Untouched Holdout Test Dataset
        c_feats_test, p_feats_test, cp_agg_test = self.build_features_for_cutoff(
            txn_df, cust_df, prod_df, cutoff_date="2026-06-01"
        )
        test_df = self.create_labeled_dataset(
            txn_df, c_feats_test, p_feats_test, cp_agg_test,
            target_start_date="2026-06-01", target_end_date="2026-10-24",
            negative_ratio=negative_ratio
        )

        return dev_df, test_df
