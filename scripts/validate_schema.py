import os

import psycopg
from dotenv import load_dotenv


load_dotenv()

database_url = os.getenv("DATABASE_URL")

if not database_url:
    raise RuntimeError("DATABASE_URL not found in .env")


with psycopg.connect(database_url) as conn:
    with conn.cursor() as cur:

        # ---------------------------------------------------------
        # 1. Columns
        # ---------------------------------------------------------
        cur.execute("""
            SELECT
                table_name,
                column_name,
                data_type,
                is_nullable
            FROM information_schema.columns
            WHERE table_schema = 'public'
            ORDER BY table_name, ordinal_position;
        """)

        columns = cur.fetchall()

        print("\n=== COLUMNS ===")

        current_table = None

        for table, column, data_type, nullable in columns:
            if table != current_table:
                print(f"\n[{table}]")
                current_table = table

            print(
                f"  {column} | {data_type} | nullable={nullable}"
            )

        # ---------------------------------------------------------
        # 2. Primary Keys
        # ---------------------------------------------------------
        cur.execute("""
            SELECT
                tc.table_name,
                kcu.column_name,
                kcu.ordinal_position
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
                ON tc.constraint_name = kcu.constraint_name
                AND tc.table_schema = kcu.table_schema
            WHERE tc.constraint_type = 'PRIMARY KEY'
              AND tc.table_schema = 'public'
            ORDER BY tc.table_name, kcu.ordinal_position;
        """)

        primary_keys = cur.fetchall()

        print("\n=== PRIMARY KEYS ===")

        current_table = None

        for table, column, position in primary_keys:
            if table != current_table:
                print(f"\n[{table}]")
                current_table = table

            print(f"  {column}")

        # ---------------------------------------------------------
        # 3. Foreign Keys
        # ---------------------------------------------------------
        cur.execute("""
            SELECT
                tc.table_name,
                kcu.column_name,
                ccu.table_name AS referenced_table,
                ccu.column_name AS referenced_column
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
                ON tc.constraint_name = kcu.constraint_name
                AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage ccu
                ON tc.constraint_name = ccu.constraint_name
                AND tc.table_schema = ccu.table_schema
            WHERE tc.constraint_type = 'FOREIGN KEY'
              AND tc.table_schema = 'public'
            ORDER BY tc.table_name, kcu.column_name;
        """)

        foreign_keys = cur.fetchall()

        print("\n=== FOREIGN KEYS ===")

        for table, column, ref_table, ref_column in foreign_keys:
            print(
                f"  {table}.{column} "
                f"-> {ref_table}.{ref_column}"
            )


print("\nSchema validation completed.")