import psycopg
from backend.app.config import settings

DATABASE_URL = settings.database_url


def evaluate_product(
    product_id: str,
    reward_context: bool = False,
    promotion_context: bool = False,
    express_context: bool = False,
) -> dict:
    """
    Evaluate a product against the deterministic business constraints.

    Hard constraints:
    - Product must be active.
    - Inventory must be known and greater than zero.
    - Gross margin must be at least 10%.

    Context-dependent constraints:
    - Reward eligibility applies in reward context.
    - Promotion eligibility applies in promotion context.
    - Shipping threshold applies in express context.

    Returns:
        {
            "product_id": str,
            "decision": "PASS" | "EXCLUDE",
            "reasons": list[str],
            "flags": list[str],
        }
    """

    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:

            # --------------------------------------------------
            # Fetch product + operational data
            # --------------------------------------------------
            cur.execute(
                """
                SELECT
                    p.product_id,
                    p.product_status,
                    oc.available_stock,
                    oc.inventory_status,
                    oc.gross_margin_pct,
                    oc.shipping_days,
                    oc.reward_eligible,
                    oc.promotion_eligible
                FROM products p
                JOIN operational_catalogue oc
                    ON p.product_id = oc.product_id
                WHERE p.product_id = %s;
                """,
                (product_id,),
            )

            row = cur.fetchone()

            if row is None:
                raise ValueError(
                    f"Product or operational catalogue record not found: "
                    f"{product_id}"
                )

            (
                product_id,
                product_status,
                available_stock,
                inventory_status,
                gross_margin_pct,
                shipping_days,
                reward_eligible,
                promotion_eligible,
            ) = row

    reasons = []
    flags = []

    # ----------------------------------------------------------
    # RULE_STATUS_001
    # Product must be active.
    # ----------------------------------------------------------
    if product_status != "active":
        reasons.append(
            f"Product status is '{product_status}', not active."
        )

    # ----------------------------------------------------------
    # RULE_STK_001
    # Known zero / negative inventory → EXCLUDE
    # ----------------------------------------------------------
    if available_stock is not None and available_stock <= 0:
        reasons.append("Product is out of stock.")

    # ----------------------------------------------------------
    # RULE_STK_002
    # Unknown inventory → EXCLUDE
    #
    # Fail-safe behavior:
    # unknown inventory is NOT treated as available.
    # ----------------------------------------------------------
    if available_stock is None:
        reasons.append("Inventory availability is unknown.")

    # ----------------------------------------------------------
    # RULE_MAR_001
    # Margin below 10% → EXCLUDE
    # ----------------------------------------------------------
    if gross_margin_pct < 0.10:
        reasons.append(
            f"Gross margin ({gross_margin_pct:.2%}) "
            "is below the 10% minimum."
        )

    # ----------------------------------------------------------
    # RULE_REW_001
    # Reward context only
    # ----------------------------------------------------------
    if reward_context and not reward_eligible:
        reasons.append(
            "Product is not reward eligible."
        )

    # ----------------------------------------------------------
    # RULE_PRO_001
    # Promotion context only
    # ----------------------------------------------------------
    if promotion_context and not promotion_eligible:
        reasons.append(
            "Product is not promotion eligible."
        )

    # ----------------------------------------------------------
    # RULE_FUL_001
    # Express context only
    # ----------------------------------------------------------
    if express_context and shipping_days > 7:
        flags.append(
            f"Shipping time ({shipping_days} days) exceeds "
            "the 7-day express threshold."
        )

    # ----------------------------------------------------------
    # Final deterministic decision
    # ----------------------------------------------------------
    decision = "EXCLUDE" if reasons else "PASS"

    return {
        "product_id": product_id,
        "decision": decision,
        "reasons": reasons,
        "flags": flags,
    }