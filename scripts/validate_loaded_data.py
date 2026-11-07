import os

import psycopg
from dotenv import load_dotenv


load_dotenv()

database_url = os.getenv("DATABASE_URL")

if not database_url:
    raise RuntimeError("DATABASE_URL not found in .env")


with psycopg.connect(database_url) as conn:
    with conn.cursor() as cur:

        print("=" * 60)
        print("LOADED SYNTHETIC DATA VALIDATION")
        print("=" * 60)

        # ----------------------------------------------------
        # 1. Critical product records
        # ----------------------------------------------------

        print("\n=== CRITICAL PRODUCT TEST CASES ===")

        cur.execute("""
            SELECT
                p.product_id,
                p.product_name,
                p.product_status,
                o.available_stock,
                o.gross_margin_pct,
                o.reward_eligible,
                o.promotion_eligible
            FROM products p
            JOIN operational_catalogue o
                ON p.product_id = o.product_id
            WHERE p.product_id IN (
                'PROD_0001',
                'PROD_0002',
                'PROD_0003',
                'PROD_0004',
                'PROD_0007',
                'PROD_0036',
                'PROD_0044'
            )
            ORDER BY p.product_id;
        """)

        for row in cur.fetchall():
            print(row)

        # ----------------------------------------------------
        # 2. Unknown inventory
        # ----------------------------------------------------

        print("\n=== UNKNOWN INVENTORY ===")

        cur.execute("""
            SELECT product_id
            FROM operational_catalogue
            WHERE available_stock IS NULL;
        """)

        unknown_inventory = cur.fetchall()

        print(f"Products with unknown inventory: {len(unknown_inventory)}")

        for row in unknown_inventory:
            print(f"  - {row[0]}")

        # ----------------------------------------------------
        # 3. Out-of-stock products
        # ----------------------------------------------------

        print("\n=== OUT OF STOCK ===")

        cur.execute("""
            SELECT product_id, available_stock
            FROM operational_catalogue
            WHERE available_stock <= 0
            ORDER BY product_id;
        """)

        for row in cur.fetchall():
            print(f"  - {row[0]} | stock={row[1]}")

        # ----------------------------------------------------
        # 4. Low-margin products
        # ----------------------------------------------------

        print("\n=== LOW MARGIN ===")

        cur.execute("""
            SELECT product_id, gross_margin_pct
            FROM operational_catalogue
            WHERE gross_margin_pct < 0.10
            ORDER BY product_id;
        """)

        for row in cur.fetchall():
            print(f"  - {row[0]} | margin={row[1]}")

        # ----------------------------------------------------
        # 5. Discontinued products
        # ----------------------------------------------------

        print("\n=== DISCONTINUED PRODUCTS ===")

        cur.execute("""
            SELECT product_id, product_status
            FROM products
            WHERE product_status != 'active'
            ORDER BY product_id;
        """)

        for row in cur.fetchall():
            print(f"  - {row[0]} | status={row[1]}")

        # ----------------------------------------------------
        # 6. Policy rules
        # ----------------------------------------------------

        print("\n=== POLICY RULES ===")

        cur.execute("""
            SELECT
                rule_id,
                rule_type,
                threshold,
                operator,
                action,
                priority,
                enabled
            FROM policy_rules
            ORDER BY priority, rule_id;
        """)

        for row in cur.fetchall():
            print(f"  - {row}")

        # ----------------------------------------------------
        # 7. Foreign-key orphan checks
        # ----------------------------------------------------

        print("\n=== FOREIGN KEY CHECKS ===")

        checks = {
            "transactions -> customers": """
                SELECT COUNT(*)
                FROM transactions t
                LEFT JOIN customers c
                    ON t.customer_id = c.customer_id
                WHERE c.customer_id IS NULL;
            """,

            "transactions -> products": """
                SELECT COUNT(*)
                FROM transactions t
                LEFT JOIN products p
                    ON t.product_id = p.product_id
                WHERE p.product_id IS NULL;
            """,

            "baskets -> customers": """
                SELECT COUNT(*)
                FROM baskets b
                LEFT JOIN customers c
                    ON b.customer_id = c.customer_id
                WHERE c.customer_id IS NULL;
            """,

            "baskets -> products": """
                SELECT COUNT(*)
                FROM baskets b
                LEFT JOIN products p
                    ON b.product_id = p.product_id
                WHERE p.product_id IS NULL;
            """,

            "interactions -> customers": """
                SELECT COUNT(*)
                FROM customer_product_interactions i
                LEFT JOIN customers c
                    ON i.customer_id = c.customer_id
                WHERE c.customer_id IS NULL;
            """,

            "interactions -> products": """
                SELECT COUNT(*)
                FROM customer_product_interactions i
                LEFT JOIN products p
                    ON i.product_id = p.product_id
                WHERE p.product_id IS NULL;
            """,

            "operational_catalogue -> products": """
                SELECT COUNT(*)
                FROM operational_catalogue o
                LEFT JOIN products p
                    ON o.product_id = p.product_id
                WHERE p.product_id IS NULL;
            """,
        }

        for name, query in checks.items():
            cur.execute(query)
            count = cur.fetchone()[0]

            status = "PASS" if count == 0 else "FAIL"

            print(f"{status}: {name} | orphan rows={count}")


print("\n" + "=" * 60)
print("Loaded-data validation completed.")
print("=" * 60)