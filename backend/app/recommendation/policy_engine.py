import psycopg
from backend.app.config import settings

DATABASE_URL = settings.database_url
FRESH_DATA_STATUSES = {"verified_fresh", "fresh"}


def evaluate_product(
    product_id: str,
    reward_context: bool = False,
    promotion_context: bool = False,
    express_context: bool = False,
    requested_discount_pct: float | None = None,
) -> dict:
    """
    Evaluate a product against the deterministic business constraints.

    Hard constraints:
    - Product must be active.
    - Inventory must be known (not NULL and not 'unknown') and greater than zero.
    - Operational catalogue record must not be stale/unverified.
    - Gross margin must be at least 10%.

    Context-dependent constraints:
    - Reward eligibility applies in reward context.
    - Promotion eligibility applies in promotion context.
    - Discount limits apply when requested_discount_pct is supplied.
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
                    oc.promotion_eligible,
                    oc.data_freshness_status,
                    oc.max_discount_pct
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

            data_freshness_status = "verified_fresh"
            max_discount_pct = None
            if len(row) >= 10:
                (
                    product_id,
                    product_status,
                    available_stock,
                    inventory_status,
                    gross_margin_pct,
                    shipping_days,
                    reward_eligible,
                    promotion_eligible,
                    data_freshness_status,
                    max_discount_pct,
                ) = row[:10]
            elif len(row) == 9:
                (
                    product_id,
                    product_status,
                    available_stock,
                    inventory_status,
                    gross_margin_pct,
                    shipping_days,
                    reward_eligible,
                    promotion_eligible,
                    data_freshness_status,
                ) = row
            else:
                (
                    product_id,
                    product_status,
                    available_stock,
                    inventory_status,
                    gross_margin_pct,
                    shipping_days,
                    reward_eligible,
                    promotion_eligible,
                ) = row[:8]

    reasons = []
    flags = []

    # ----------------------------------------------------------
    # RULE_STATUS_001: Product must be active.
    # ----------------------------------------------------------
    if product_status != "active":
        reasons.append(
            f"Product status is '{product_status}', not active."
        )

    # ----------------------------------------------------------
    # RULE_STK_001: Known zero / negative inventory -> EXCLUDE
    # ----------------------------------------------------------
    if available_stock is not None and available_stock <= 0:
        reasons.append("Product is out of stock.")

    # ----------------------------------------------------------
    # RULE_STK_002: Unknown inventory -> EXCLUDE (fail-safe)
    # ----------------------------------------------------------
    if available_stock is None or str(inventory_status or "").strip().lower() == "unknown":
        reasons.append("Inventory availability is unknown.")

    # ----------------------------------------------------------
    # RULE_FRESH_001: Stale or unverified operational data -> EXCLUDE
    # ----------------------------------------------------------
    if (
        data_freshness_status is None
        or str(data_freshness_status).strip().lower() not in FRESH_DATA_STATUSES
    ):
        reasons.append(
            f"Operational inventory data is stale or unverified ({data_freshness_status})."
        )

    # ----------------------------------------------------------
    # RULE_MAR_001: Margin below 10% -> EXCLUDE
    # ----------------------------------------------------------
    if gross_margin_pct < 0.10:
        reasons.append(
            f"Gross margin ({gross_margin_pct:.2%}) "
            "is below the 10% minimum."
        )

    # ----------------------------------------------------------
    # RULE_REW_001: Reward context only
    # ----------------------------------------------------------
    if reward_context and not reward_eligible:
        reasons.append(
            "Product is not reward eligible."
        )

    # ----------------------------------------------------------
    # RULE_PRO_001: Promotion context only
    # ----------------------------------------------------------
    if promotion_context and not promotion_eligible:
        reasons.append(
            "Product is not promotion eligible."
        )

    # ----------------------------------------------------------
    # RULE_DSC_001: Discount limit check
    # ----------------------------------------------------------
    if (
        requested_discount_pct is not None
        and max_discount_pct is not None
        and float(requested_discount_pct) > float(max_discount_pct)
    ):
        reasons.append(
            f"Requested discount ({float(requested_discount_pct):.2%}) exceeds "
            f"maximum permitted limit ({float(max_discount_pct):.2%})."
        )

    # ----------------------------------------------------------
    # RULE_FUL_001: Express context only
    # ----------------------------------------------------------
    if express_context and shipping_days > 7:
        flags.append(
            f"Shipping time ({shipping_days} days) exceeds "
            "the 7-day express threshold."
        )

    decision = "EXCLUDE" if reasons else "PASS"

    return {
        "product_id": product_id,
        "decision": decision,
        "reasons": reasons,
        "flags": flags,
    }
