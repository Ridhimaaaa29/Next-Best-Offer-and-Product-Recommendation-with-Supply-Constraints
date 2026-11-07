from backend.app.recommendation.candidate_generator import (
    generate_candidates,
)


customer_id = "CUST_0001"

candidates = generate_candidates(
    customer_id=customer_id,
    limit=20,
)

print("=" * 60)
print("CANDIDATE GENERATION")
print("=" * 60)

print(f"\nCustomer: {customer_id}")
print(f"Candidates generated: {len(candidates)}")

print("\nCandidates:")

for index, candidate in enumerate(candidates, start=1):
    print(
        f"{index:2}. "
        f"{candidate['product_id']} | "
        f"{candidate['product_name']} | "
        f"category={candidate['category']} | "
        f"popularity={candidate['product_popularity']}"
    )