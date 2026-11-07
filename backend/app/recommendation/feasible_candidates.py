from backend.app.recommendation.candidate_generator import generate_candidates
from backend.app.recommendation.policy_engine import evaluate_product


def get_feasible_candidates(
    customer_id: str,
    limit: int = 20,
    reward_context: bool = False,
    promotion_context: bool = False,
    express_context: bool = False,
) -> dict:
    """
    Generate candidate products and apply deterministic
    business constraints.

    Returns both the complete candidate pool and the
    candidates that passed the policy engine.
    """

    candidates = generate_candidates(
        customer_id=customer_id,
        limit=limit,
    )

    evaluated_candidates = []

    for candidate in candidates:
        evaluation = evaluate_product(
            product_id=candidate["product_id"],
            reward_context=reward_context,
            promotion_context=promotion_context,
            express_context=express_context,
        )

        evaluated_candidates.append(
            {
                **candidate,
                "decision": evaluation["decision"],
                "reasons": evaluation["reasons"],
                "flags": evaluation["flags"],
            }
        )

    feasible_candidates = [
        candidate
        for candidate in evaluated_candidates
        if candidate["decision"] == "PASS"
    ]

    return {
        "customer_id": customer_id,
        "candidate_count": len(candidates),
        "feasible_count": len(feasible_candidates),
        "candidates": evaluated_candidates,
        "feasible_candidates": feasible_candidates,
    }