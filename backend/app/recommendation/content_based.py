"""
Content-Based Recommender.
Status: NOT YET IMPLEMENTED / PLANNED FOR FUTURE ITERATION.
This file is a placeholder conforming to the target project architecture.
"""

from typing import List, Tuple, Any, Optional
import pandas as pd


class ContentBasedRecommender:
    """
    Placeholder for item-feature cosine similarity / vector embeddings (e.g. Milvus / TF-IDF).
    Currently, candidate scoring uses category affinity, product popularity, ratings, and ML propensity.
    """

    def __init__(self):
        pass

    def fit(self, product_features: pd.DataFrame) -> None:
        raise NotImplementedError("Content-based recommendation is scheduled for a future iteration.")

    def recommend(self, product_id: str, top_n: int = 5) -> List[Tuple[str, float]]:
        raise NotImplementedError("Content-based recommendation is scheduled for a future iteration.")
