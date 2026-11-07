from sqlalchemy.orm import Session

from backend.app.db.repositories import CustomerRepository


def get_customer_context(customer_id: str, session: Session) -> dict:
    """
    Retrieve recommendation-relevant context for a customer.
    """
    repository = CustomerRepository(session)
    return {
        "customer": repository.get_customer_context(customer_id),
        "interactions": repository.get_interaction_history(customer_id),
    }