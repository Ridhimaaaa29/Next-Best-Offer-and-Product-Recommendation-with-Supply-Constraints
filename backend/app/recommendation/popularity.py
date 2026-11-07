"""
Popularity-based baseline candidate scorer / ranker.
"""

from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np


class PopularityRanker:
    """
    Computes popularity-based recommendation candidates from interaction counts.
    """

    def __init__(self, top_k: int = 10):
        self.top_k = top_k
        self.popular_items: List[str] = []
        self.popular_scores: Dict[str, float] = {}

    def fit(self, train_df: pd.DataFrame, item_col: str = "product_id", order_col: str = "transaction_id") -> None:
        if train_df.empty:
            return
        pop = (
            train_df.groupby(item_col)
            .agg(order_count=(order_col, "nunique"))
            .reset_index()
            .sort_values("order_count", ascending=False)
        )
        max_orders = pop["order_count"].max() if not pop.empty else 1.0
        pop["score"] = pop["order_count"] / max(1.0, max_orders)
        self.popular_items = pop[item_col].tolist()
        self.popular_scores = dict(zip(pop[item_col], pop["score"]))

    def recommend(
        self,
        customer_history: Optional[set] = None,
        top_n: int = 5,
        exclude_purchased: bool = True,
    ) -> List[tuple]:
        history = customer_history or set()
        recs = []
        for item in self.popular_items:
            if exclude_purchased and item in history:
                continue
            recs.append((item, self.popular_scores.get(item, 0.0)))
            if len(recs) >= top_n:
                break
        return recs
