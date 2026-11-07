import os

import psycopg
from dotenv import load_dotenv


load_dotenv()

database_url = os.getenv("DATABASE_URL")

if not database_url:
    raise RuntimeError("DATABASE_URL not found in .env")


with psycopg.connect(database_url) as conn:
    with conn.cursor() as cur:

        # This will be checked after data loading.
        # For now, verify that the database schema has the
        # expected relationship columns.

        cur.execute("""
            SELECT
                table_name,
                column_name
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name IN ('baskets', 'transactions')
              AND column_name IN ('transaction_id', 'product_id')
            ORDER BY table_name, column_name;
        """)

        rows = cur.fetchall()

print("Relationship columns found:")

for table, column in rows:
    print(f"- {table}.{column}")