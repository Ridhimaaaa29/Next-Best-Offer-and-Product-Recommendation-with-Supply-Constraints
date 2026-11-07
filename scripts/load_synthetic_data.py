import csv
import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv


# ------------------------------------------------------------
# Configuration
# ------------------------------------------------------------

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL not found in .env")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "synthetic"


# ------------------------------------------------------------
# Table configuration
# ------------------------------------------------------------

TABLES = [
    ("customers.csv", "customers"),
    ("products.csv", "products"),
    ("transactions.csv", "transactions"),
    ("baskets.csv", "baskets"),
    ("customer_product_interactions.csv", "customer_product_interactions"),
    ("operational_catalogue.csv", "operational_catalogue"),
    ("policy_rules.csv", "policy_rules"),
]


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------

def read_csv(filename):
    """Read a synthetic CSV file and return rows + column names."""

    file_path = DATA_DIR / filename

    if not file_path.exists():
        raise FileNotFoundError(
            f"Synthetic data file not found: {file_path}"
        )

    with file_path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)

        rows = list(reader)
        columns = reader.fieldnames

    if not columns:
        raise ValueError(f"No columns found in {filename}")

    return rows, columns


def normalize_value(value):
    """
    Convert CSV empty values to Python None so PostgreSQL
    stores them as SQL NULL.
    """

    if value is None:
        return None

    value = value.strip()

    if value == "":
        return None

    return value


# ------------------------------------------------------------
# Main loading process
# ------------------------------------------------------------

def main():

    print("=" * 60)
    print("SYNTHETIC DATA -> NEON")
    print("=" * 60)

    with psycopg.connect(DATABASE_URL) as conn:

        # ----------------------------------------------------
        # Check that all expected tables exist
        # ----------------------------------------------------

        with conn.cursor() as cur:

            cur.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public';
            """)

            existing_tables = {
                row[0]
                for row in cur.fetchall()
            }

        expected_tables = {
            table_name
            for _, table_name in TABLES
        }

        missing_tables = expected_tables - existing_tables

        if missing_tables:
            raise RuntimeError(
                f"Missing database tables: {sorted(missing_tables)}"
            )

        print("[OK] All 7 Neon tables found")

        # ----------------------------------------------------
        # Load each table
        # ----------------------------------------------------

        for filename, table_name in TABLES:

            rows, columns = read_csv(filename)

            print(f"\nLoading {filename}")
            print(f"  Target table : {table_name}")
            print(f"  CSV rows     : {len(rows)}")

            if not rows:
                print("  No rows found. Skipping.")
                continue

            column_sql = ", ".join(columns)
            placeholder_sql = ", ".join(
                ["%s"] * len(columns)
            )

            insert_sql = f"""
                INSERT INTO {table_name} ({column_sql})
                VALUES ({placeholder_sql});
            """

            values = [
                tuple(
                    normalize_value(row[column])
                    for column in columns
                )
                for row in rows
            ]

            try:
                with conn.cursor() as cur:
                    cur.executemany(insert_sql, values)

                conn.commit()

            except Exception:
                conn.rollback()
                raise

            print(f"  [OK] Inserted {len(rows)} rows")

    print("\n" + "=" * 60)
    print("Synthetic data loading completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()