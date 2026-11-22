"""
Content-Based Semantic Vector Similarity Recommender.
Constructs TF-IDF vector embeddings across product catalogue attributes
and calculates pairwise cosine similarity to discover semantically related products.
"""
from typing import List, Tuple, Dict, Any, Optional
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class ContentBasedRecommender:
    """
    Vector similarity recommender utilizing TF-IDF feature embeddings and cosine similarity.
    Calculates pairwise semantic vectors across product name, category, subcategory, brand, and pricing tier.
    """

    def __init__(self):
        self.vectorizer = TfidfVectorizer(stop_words="english")
        self.product_df: Optional[pd.DataFrame] = None
        self.embeddings: Optional[np.ndarray] = None
        self.similarity_matrix: Optional[np.ndarray] = None
        self.id_to_idx: Dict[str, int] = {}
        self.idx_to_id: Dict[int, str] = {}

    def fit(self, products_df: pd.DataFrame) -> "ContentBasedRecommender":
        """
        Fits the vector space model across catalogue products.
        """
        self.product_df = products_df.copy().reset_index(drop=True)
        
        # Build composite textual representation for embedding vectorization
        corpus = []
        for _, row in self.product_df.iterrows():
            name = str(row.get("product_name", ""))
            category = str(row.get("category", ""))
            subcategory = str(row.get("subcategory", ""))
            brand = str(row.get("brand", ""))
            rating = f"rated_{int(round(float(row.get('product_rating', 4.0))))}_stars"
            price = float(row.get("unit_price", 0.0))
            price_tier = "budget_tier" if price < 30 else ("mid_tier" if price < 100 else "premium_tier")
            
            text_rep = f"{name} {category} {subcategory} {brand} {price_tier} {rating}"
            corpus.append(text_rep)

        self.embeddings = self.vectorizer.fit_transform(corpus).toarray()
        self.similarity_matrix = cosine_similarity(self.embeddings, self.embeddings)

        self.id_to_idx = {row["product_id"]: idx for idx, row in self.product_df.iterrows()}
        self.idx_to_id = {idx: row["product_id"] for idx, row in self.product_df.iterrows()}
        return self

    def recommend(self, product_id: str, top_n: int = 5) -> List[Tuple[str, float]]:
        """
        Returns top-N most semantically similar products and cosine similarity scores.
        """
        if self.similarity_matrix is None or not self.id_to_idx:
            raise RuntimeError("Recommender is not fitted. Call fit(products_df) first.")

        if product_id not in self.id_to_idx:
            return []

        idx = self.id_to_idx[product_id]
        scores = self.similarity_matrix[idx]
        
        # Sort descending, excluding self (similarity == 1.0)
        ranked_indices = np.argsort(scores)[::-1]
        results = []
        for i in ranked_indices:
            cand_id = self.idx_to_id[i]
            if cand_id != product_id:
                sim_score = float(scores[i])
                results.append((cand_id, round(sim_score, 4)))
                if len(results) >= top_n:
                    break

        return results

    def get_similar_products_detailed(self, product_id: str, top_n: int = 5) -> List[Dict[str, Any]]:
        """
        Returns top-N similar products with full metadata and vector similarity score.
        """
        sim_pairs = self.recommend(product_id, top_n=top_n)
        if not sim_pairs or self.product_df is None:
            return []

        output = []
        for pid, score in sim_pairs:
            matches = self.product_df[self.product_df["product_id"] == pid]
            if not matches.empty:
                item_dict = matches.iloc[0].to_dict()
                item_dict["similarity_score"] = score
                item_dict["cosine_similarity_pct"] = f"{score * 100:.1f}%"
                output.append(item_dict)
        return output


_GLOBAL_CONTENT_RECOMMENDER: Optional[ContentBasedRecommender] = None


def get_content_recommender(products_df: Optional[pd.DataFrame] = None) -> ContentBasedRecommender:
    """Singleton getter for the ContentBasedRecommender."""
    global _GLOBAL_CONTENT_RECOMMENDER
    if _GLOBAL_CONTENT_RECOMMENDER is None:
        rec = ContentBasedRecommender()
        if products_df is not None:
            rec.fit(products_df)
        _GLOBAL_CONTENT_RECOMMENDER = rec
    elif products_df is not None and _GLOBAL_CONTENT_RECOMMENDER.similarity_matrix is None:
        _GLOBAL_CONTENT_RECOMMENDER.fit(products_df)
    return _GLOBAL_CONTENT_RECOMMENDER
