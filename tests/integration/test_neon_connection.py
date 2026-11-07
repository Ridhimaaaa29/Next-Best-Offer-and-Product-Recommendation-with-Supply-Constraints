import os
from dotenv import load_dotenv
import psycopg

load_dotenv()

database_url = os.getenv("DATABASE_URL")

if not database_url:
    raise RuntimeError("DATABASE_URL not found in .env")

try:
    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1;")
            result = cur.fetchone()

    print("Neon connection successful!")
    print("SELECT 1 result:", result)

except Exception as e:
    print("Neon connection failed.")
    print(type(e).__name__, ":", e)