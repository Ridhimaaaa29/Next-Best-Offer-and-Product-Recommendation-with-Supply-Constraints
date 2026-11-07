import os

import psycopg
from dotenv import load_dotenv


load_dotenv()

database_url = os.getenv("DATABASE_URL")

if not database_url:
    raise RuntimeError("DATABASE_URL not found in .env")


tables = [
    "customers",
    "products",
    "transactions",
    "baskets",
    "customer_product_interactions",
    "operational_catalogue",
    "policy_rules",
]


with psycopg.connect(database_url) as conn:
    with conn.cursor() as cur:

        print("=" * 50)
        print("NEON DATA COUNTS")
        print("=" * 50)

        for table in tables:
            cur.execute(f"SELECT COUNT(*) FROM {table};")
            count = cur.fetchone()[0]

            print(f"{table:<35} {count}")

        print("=" * 50)