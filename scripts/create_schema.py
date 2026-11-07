import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv


load_dotenv()

database_url = os.getenv("DATABASE_URL")

if not database_url:
    raise RuntimeError("DATABASE_URL not found in .env")

schema_path = Path(__file__).parent / "schema.sql"
schema_sql = schema_path.read_text(encoding="utf-8")

try:
    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(schema_sql)

        conn.commit()

    print("Database schema created successfully!")
    print("7 core tables are ready in Neon.")

except Exception as e:
    print("Schema creation failed.")
    print(type(e).__name__, ":", e)
    raise
