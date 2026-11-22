"""
Unit tests for ContentBasedRecommender.
Tests semantic vector indexing and cosine similarity rankings across product attributes.
"""
import pandas as pd
import pytest

from backend.app.recommendation.content_based import ContentBasedRecommender, get_content_recommender


@pytest.fixture
def sample_catalogue_df():
    return pd.DataFrame([
        {
            "product_id": "PROD_0001",
            "product_name": "Wireless Noise-Cancelling Headphones",
            "category": "Electronics",
            "subcategory": "Audio",
            "brand": "AudioMax",
            "unit_price": 199.99,
            "product_rating": 4.5,
        },
        {
            "product_id": "PROD_0007",
            "product_name": "65W GaN Compact Wall Charger",
            "category": "Electronics",
            "subcategory": "Accessories",
            "brand": "TechPro",
            "unit_price": 34.99,
            "product_rating": 4.3,
        },
        {
            "product_id": "PROD_0006",
            "product_name": "Magnetic Wireless Charging Stand",
            "category": "Electronics",
            "subcategory": "Accessories",
            "brand": "TechPro",
            "unit_price": 45.99,
            "product_rating": 4.2,
        },
        {
            "product_id": "PROD_0018",
            "product_name": "Air Fryer Deluxe with LED Display",
            "category": "Home & Kitchen",
            "subcategory": "Cookware",
            "brand": "KitchenPro",
            "unit_price": 89.99,
            "product_rating": 4.6,
        },
    ])


def test_content_recommender_fit_and_recommend(sample_catalogue_df):
    recommender = ContentBasedRecommender()
    recommender.fit(sample_catalogue_df)

    # Wall Charger should be most similar to Wireless Charging Stand (same brand, category, subcategory)
    recommendations = recommender.recommend("PROD_0007", top_n=2)
    assert len(recommendations) == 2
    top_match_id, top_score = recommendations[0]
    assert top_match_id == "PROD_0006"
    assert top_score > 0.0


def test_content_recommender_detailed_metadata(sample_catalogue_df):
    recommender = ContentBasedRecommender()
    recommender.fit(sample_catalogue_df)

    details = recommender.get_similar_products_detailed("PROD_0007", top_n=2)
    assert len(details) == 2
    assert details[0]["product_id"] == "PROD_0006"
    assert "similarity_score" in details[0]
    assert "cosine_similarity_pct" in details[0]


def test_content_recommender_unfitted_raises():
    recommender = ContentBasedRecommender()
    with pytest.raises(RuntimeError, match="Recommender is not fitted"):
        recommender.recommend("PROD_0001")


def test_content_recommender_unknown_product(sample_catalogue_df):
    recommender = ContentBasedRecommender()
    recommender.fit(sample_catalogue_df)
    assert recommender.recommend("PROD_UNKNOWN") == []

