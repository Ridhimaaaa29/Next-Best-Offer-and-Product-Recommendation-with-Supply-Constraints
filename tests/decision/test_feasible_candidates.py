from backend.app.recommendation.feasible_candidates import (
    get_feasible_candidates,
)


customer_id = "CUST_0001"

result = get_feasible_candidates(
    customer_id=customer_id,
    limit=20,
    reward_context=True,
)

print("=" * 70)
print("FEASIBLE CANDIDATES")
print("=" * 70)

print(f"\nCustomer: {result['customer_id']}")
print(f"Candidate pool: {result['candidate_count']}")
print(f"Feasible candidates: {result['feasible_count']}")

print("\nAll evaluated candidates:")

for index, candidate in enumerate(
    result["candidates"],
    start=1,
):
    print(
        f"{index:2}. "
        f"{candidate['product_id']} | "
        f"{candidate['product_name']} | "
        f"{candidate['decision']}"
    )

    for reason in candidate["reasons"]:
        print(f"      Reason: {reason}")

print("\nFeasible candidates:")

for index, candidate in enumerate(
    result["feasible_candidates"],
    start=1,
):
    print(
        f"{index:2}. "
        f"{candidate['product_id']} | "
        f"{candidate['product_name']} | "
        f"popularity={candidate['product_popularity']}"
    )