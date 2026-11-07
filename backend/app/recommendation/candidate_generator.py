import psycopg
from backend.app.config import settings

DATABASE_URL = settings.database_url


def generate_candidates(
    customer_id: str,
    limit: int = 20,
) -> list[dict]:
    """
    Generate a candidate pool for a customer.

    Candidates are:
    - not previously interacted with by the customer
    - from the customer's preferred category
    - ordered by product popularity
    """

    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:

            cur.execute(
                """
                SELECT preferred_category
                FROM customers
                WHERE customer_id = %s;
                """,
                (customer_id,),
            )

            customer_row = cur.fetchone()

            if customer_row is None:
                raise ValueError(
                    f"Customer not found: {customer_id}"
                )

            preferred_category = customer_row[0]

            cur.execute(
                """
                SELECT
                    p.product_id,
                    p.product_name,
                    p.category,
                    p.subcategory,
                    p.brand,
                    p.unit_price,
                    p.product_rating,
                    p.product_popularity,
                    p.product_status
                FROM products p
                WHERE p.category = %s
                  AND p.product_id NOT IN (
                      SELECT i.product_id
                      FROM customer_product_interactions i
                      WHERE i.customer_id = %s
                  )
                ORDER BY
                    p.product_popularity DESC,
                    p.product_rating DESC
                LIMIT %s;
                """,
                (
                    preferred_category,
                    customer_id,
                    limit,
                ),
            )

            rows = cur.fetchall()

    columns = [
        "product_id",
        "product_name",
        "category",
        "subcategory",
        "brand",
        "unit_price",
        "product_rating",
        "product_popularity",
        "product_status",
    ]

    return [
        dict(zip(columns, row))
        for row in rows
    ]