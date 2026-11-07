from backend.app.recommendation.customer_context import (
    get_customer_context,
)
from backend.app.db.session import get_db_context


customer_id = "CUST_0001"

with get_db_context() as session:
    context = get_customer_context(customer_id, session)

print("=" * 60)
print("CUSTOMER CONTEXT")
print("=" * 60)

print("\nCustomer:")
for key, value in context["customer"].items():
    print(f"  {key}: {value}")

print(
    f"\nInteraction records: "
    f"{len(context['interactions'])}"
)

print("\nFirst 5 interactions:")

for interaction in context["interactions"][:5]:
    print(f"  {interaction}")