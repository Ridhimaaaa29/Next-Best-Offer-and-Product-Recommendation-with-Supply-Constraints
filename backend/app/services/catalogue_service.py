"""
Catalogue Service.
Provides catalog queries and operational stock lookups.
"""

from typing import Dict, Any, Optional
import psycopg
from backend.app.config import settings

DATABASE_URL = settings.database_url


class CatalogueService:
    def get_product_details(self, product_id: str) -> Optional[Dict[str, Any]]:
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT p.product_id, p.product_name, p.category, p.subcategory,
                           p.brand, p.unit_price, p.product_rating, p.product_popularity,
                           p.product_status, oc.available_stock, oc.gross_margin_pct
                    FROM products p
                    LEFT JOIN operational_catalogue oc ON p.product_id = oc.product_id
                    WHERE p.product_id = %s;
                    """,
                    (product_id,),
                )
                row = cur.fetchone()
                if not row:
                    return None
                cols = [
                    "product_id", "product_name", "category", "subcategory",
                    "brand", "unit_price", "product_rating", "product_popularity",
                    "product_status", "available_stock", "gross_margin_pct",
                ]
                return dict(zip(cols, row))
