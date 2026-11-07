from backend.app.recommendation.policy_engine import evaluate_product


TEST_PRODUCTS = [
    ("PROD_0001", {}),
    ("PROD_0002", {}),
    ("PROD_0003", {}),
    ("PROD_0004", {}),
    ("PROD_0007", {"reward_context": True}),
    ("PROD_0036", {}),
    ("PROD_0044", {}),
]


print("=" * 70)
print("POLICY / CONSTRAINT ENGINE")
print("=" * 70)

for product_id, context in TEST_PRODUCTS:
    result = evaluate_product(
        product_id=product_id,
        **context,
    )

    print(f"\nProduct: {product_id}")
    print(f"Decision: {result['decision']}")

    if result["reasons"]:
        print("Reasons:")
        for reason in result["reasons"]:
            print(f"  - {reason}")

    if result["flags"]:
        print("Flags:")
        for flag in result["flags"]:
            print(f"  - {flag}")

    if not result["reasons"] and not result["flags"]:
        print("No constraint violations.")