"""Local stdio MCP server exposing deterministic recommendation and decision tools."""

from __future__ import annotations

import csv
import logging
import sys
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from mcp.server.mcpserver import MCPServer
from sqlalchemy import select

from backend.app.db.models import Product, Transaction
from backend.app.db.repositories import OperationalCatalogueRepository
from backend.app.db.session import get_db_context
from backend.app.decision.baseline_ranker import rank_feasible_candidates
from backend.app.decision.laya_adapter import LayaAdapter
from backend.app.decision.weighted_engine import WeightedDecisionEngine
from backend.app.mcp.schemas import (
    CustomerContext,
    CustomerInput,
    CustomerProfile,
    DecisionEngineInput,
    DecisionEngineOutput,
    EvaluationOutput,
    FinalExclusion,
    FinalizeInput,
    FinalizeOutput,
    FinalRecommendation,
    Interaction,
    InventoryDetails,
    InventoryInput,
    PolicyInput,
    PolicyOutput,
    ProductDetailsInput,
    ProductDetailsOutput,
    PurchaseHistoryInput,
    PurchaseHistoryItem,
    PurchaseHistoryOutput,
    RecommendationInput,
    RecommendationOutput,
    SaveDecisionInput,
    SaveDecisionOutput,
    ScoredCandidate,
    ValidateFinalInput,
    ValidateFinalOutput,
)
from backend.app.recommendation.candidate_generator import generate_candidates
from backend.app.recommendation.customer_context import get_customer_context as load_customer_context
from backend.app.recommendation.policy_engine import evaluate_product
from backend.app.recommendation.recommendation_model import RecommendationModel
from backend.app.services.audit_service import AuditService


logging.basicConfig(stream=sys.stderr, level=logging.INFO)
logger = logging.getLogger("nbo.mcp.server")
server = MCPServer(
    name="nbo-deterministic-multi-agent",
    version="1.0.0",
    instructions="Deterministic supply-constrained recommendation and weighted decision tools.",
)


def _json_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def _json_record(record: dict[str, Any]) -> dict[str, Any]:
    return {key: _json_value(value) for key, value in record.items()}


@server.tool(structured_output=True)
def get_customer_context(request: CustomerInput) -> CustomerContext:
    """Retrieve a customer profile and interaction history."""
    logger.info("tool=get_customer_context customer_id=%s", request.customer_id)
    with get_db_context() as session:
        context = load_customer_context(request.customer_id, session)
    customer = _json_record(context["customer"])
    interactions = [_json_record(item) for item in context["interactions"]]
    return CustomerContext(
        customer=CustomerProfile(**customer),
        interactions=[Interaction(**item) for item in interactions],
    )


@server.tool(structured_output=True)
def generate_recommendations(request: RecommendationInput) -> RecommendationOutput:
    """Generate and score candidates without applying operational policy."""
    logger.info("tool=generate_recommendations customer_id=%s", request.customer_id)
    model = RecommendationModel()
    candidates = generate_candidates(request.customer_id, limit=request.limit)
    scored = model.rank_candidates(
        customer_id=request.customer_id,
        candidates=candidates,
        candidate_limit=request.limit,
    )
    return RecommendationOutput(
        customer_id=request.customer_id,
        candidate_count=len(scored),
        candidates=[
            ScoredCandidate(
                product_id=item.product_id,
                product_name=item.product_name,
                category=item.category,
                subcategory=item.subcategory,
                brand=item.brand,
                unit_price=item.unit_price,
                product_rating=item.product_rating,
                product_popularity=item.product_popularity,
                product_status=item.product_status,
                recommendation_score=item.score,
                score_breakdown=item.explanation.to_dict(),
            )
            for item in scored
        ],
    )


@server.tool(structured_output=True)
def get_customer_purchase_history(request: PurchaseHistoryInput) -> PurchaseHistoryOutput:
    """Retrieve verified purchase history for a customer."""
    with get_db_context() as session:
        rows = session.scalars(
            select(Transaction)
            .where(Transaction.customer_id == request.customer_id)
            .order_by(Transaction.transaction_date.desc())
            .limit(request.limit)
        ).all()
    return PurchaseHistoryOutput(
        customer_id=request.customer_id,
        transactions=[
            PurchaseHistoryItem(
                transaction_id=row.transaction_id,
                transaction_date=row.transaction_date.isoformat(),
                product_id=row.product_id,
                quantity=row.quantity,
                final_amount=float(row.final_amount),
                order_status=row.order_status,
            )
            for row in rows
        ],
    )


@server.tool(structured_output=True)
def get_product_details(request: ProductDetailsInput) -> ProductDetailsOutput:
    """Retrieve catalogue product details."""
    with get_db_context() as session:
        product = session.get(Product, request.product_id)
    if product is None:
        raise ValueError(f"Product not found: {request.product_id}")
    return ProductDetailsOutput(
        product_id=product.product_id,
        product_name=product.product_name,
        category=product.category,
        subcategory=product.subcategory,
        brand=product.brand,
        unit_price=float(product.unit_price),
        product_rating=float(product.product_rating),
        product_status=product.product_status,
    )


@server.tool(structured_output=True)
def get_inventory_details(request: InventoryInput) -> InventoryDetails:
    """Retrieve operational inventory and fulfilment data for one product."""
    logger.info("tool=get_inventory_details product_id=%s", request.product_id)
    try:
        with get_db_context() as session:
            row = OperationalCatalogueRepository(session).get_product_policy_data(request.product_id)
        if row is None:
            return InventoryDetails(
                product_id=request.product_id,
                product_status="unknown",
                available_stock=None,
                inventory_status=None,
                gross_margin_pct=None,
                shipping_days=None,
                reward_eligible=None,
                promotion_eligible=None,
                reorder_point=None,
                max_discount_pct=None,
                data_freshness_status=None,
                verification_status="missing",
                error="Product or operational catalogue record not found.",
            )
        return InventoryDetails(
            product_id=request.product_id,
            product_status=str(row["product_status"]),
            available_stock=_json_value(row["available_stock"]),
            inventory_status=row["inventory_status"],
            gross_margin_pct=_json_value(row["gross_margin_pct"]),
            shipping_days=row["shipping_days"],
            reward_eligible=row["reward_eligible"],
            promotion_eligible=row["promotion_eligible"],
            reorder_point=row.get("reorder_point"),
            max_discount_pct=_json_value(row.get("max_discount_pct")),
            data_freshness_status=row.get("data_freshness_status"),
            verification_status="verified",
        )
    except Exception as error:
        logger.exception("tool=get_inventory_details failed product_id=%s", request.product_id)
        return InventoryDetails(
            product_id=request.product_id,
            product_status="unknown",
            available_stock=None,
            inventory_status=None,
            gross_margin_pct=None,
            shipping_days=None,
            reward_eligible=None,
            promotion_eligible=None,
            reorder_point=None,
            max_discount_pct=None,
            data_freshness_status=None,
            verification_status="failed",
            error=str(error),
        )


@server.tool(structured_output=True)
def evaluate_policy(request: PolicyInput) -> PolicyOutput:
    """Evaluate one product with the authoritative deterministic policy engine."""
    logger.info("tool=evaluate_policy product_id=%s", request.product_id)
    result = evaluate_product(
        product_id=request.product_id,
        reward_context=request.reward_context,
        promotion_context=request.promotion_context,
        express_context=request.express_context,
    )
    return PolicyOutput(
        product_id=result["product_id"],
        decision=result["decision"],
        reasons=result["reasons"],
        flags=result["flags"],
    )


@server.tool(structured_output=True)
def finalize_decision(request: FinalizeInput) -> FinalizeOutput:
    """Revalidate every candidate and return only policy-feasible products."""
    logger.info("tool=finalize_decision candidate_count=%s", len(request.candidates))
    feasible: list[FinalRecommendation] = []
    excluded: list[FinalExclusion] = []
    for candidate in request.candidates:
        result = evaluate_product(
            product_id=candidate.product_id,
            reward_context=request.reward_context,
            promotion_context=request.promotion_context,
            express_context=request.express_context,
        )
        if result["decision"] == "PASS":
            feasible.append(
                FinalRecommendation(
                    product_id=candidate.product_id,
                    product_name=candidate.product_name,
                    recommendation_score=candidate.recommendation_score,
                    policy_decision="PASS",
                    objective_scores=candidate.objective_scores,
                    weighted_score=candidate.weighted_score,
                    rank=candidate.rank,
                )
            )
        else:
            excluded.append(
                FinalExclusion(
                    product_id=candidate.product_id,
                    product_name=candidate.product_name,
                    recommendation_score=candidate.recommendation_score,
                    policy_decision="EXCLUDE",
                    policy_reasons=result["reasons"],
                )
            )
    feasible.sort(
        key=lambda item: (
            item.rank if item.rank is not None else 9999,
            -(item.weighted_score if item.weighted_score is not None else item.recommendation_score),
            -item.recommendation_score,
            item.product_id,
        )
    )
    return FinalizeOutput(
        status="SUCCESS" if feasible else "ALL_CANDIDATES_EXCLUDED",
        recommendations=feasible,
        excluded_candidates=excluded,
    )


@server.tool(structured_output=True)
def validate_final_decision(request: ValidateFinalInput) -> ValidateFinalOutput:
    """Revalidate one proposed final product with the authoritative policy."""
    result = evaluate_product(
        product_id=request.product_id,
        reward_context=request.reward_context,
        promotion_context=request.promotion_context,
        express_context=request.express_context,
    )
    return ValidateFinalOutput(
        product_id=result["product_id"],
        decision=result["decision"],
        reasons=result["reasons"],
        flags=result["flags"],
    )


@server.tool(structured_output=True)
def run_laya_decision(request: DecisionEngineInput) -> DecisionEngineOutput:
    """Run real Laya decision inference strictly over policy-feasible candidates with weighted fallback."""
    candidates = [item.model_dump() for item in request.candidates]
    weighted = WeightedDecisionEngine()
    weights: dict[str, float] = {}
    objective_scores: dict[str, dict[str, Any]] = {}
    ranked_pool = list(candidates)
    if weighted.enabled:
        try:
            weighted_eval = weighted.choose(candidates, express_context=request.express_context)
            weights = weighted_eval["weights"]
            objective_scores = weighted_eval["objective_scores"]
            ranked_pool = weighted_eval["ranked_candidates"]
        except Exception:
            ranked_pool = list(candidates)

    adapter = LayaAdapter()
    try:
        laya_result = adapter.choose(ranked_pool, express_context=request.express_context)
        chosen_id = str(laya_result["selected_product_id"])
        chosen_item = laya_result["selected"]
        rest = [c for c in ranked_pool if str(c.get("product_id")) != chosen_id]
        ordered = [chosen_item] + rest
        for idx, item in enumerate(ordered, start=1):
            item["rank"] = idx
        return DecisionEngineOutput(
            status="LAYA",
            selected_product_id=chosen_id,
            explanation=laya_result["explanation"],
            confidence=laya_result.get("confidence"),
            weights=weights,
            objective_scores=objective_scores,
            ranked_candidates=ordered,
            fallback_reason=None,
        )
    except Exception as error:
        if weighted.enabled and ranked_pool:
            chosen_id = str(ranked_pool[0]["product_id"])
            return DecisionEngineOutput(
                status="FALLBACK",
                selected_product_id=chosen_id,
                explanation=(
                    f"Laya unavailable or invalid ({error}); deterministic weighted fallback "
                    f"selected {chosen_id}."
                ),
                weights=weights,
                objective_scores=objective_scores,
                ranked_candidates=ranked_pool,
                fallback_reason=str(error),
            )
        ranked_baseline = rank_feasible_candidates(candidates, top_k=len(candidates))
        chosen_id = str(ranked_baseline[0]["product_id"])
        return DecisionEngineOutput(
            status="FALLBACK",
            selected_product_id=chosen_id,
            explanation=f"Baseline ranker selected {chosen_id} after Laya error: {error}",
            weights={},
            objective_scores={},
            ranked_candidates=ranked_baseline,
            fallback_reason=str(error),
        )


@server.tool(structured_output=True)
def run_decision_engine(request: DecisionEngineInput) -> DecisionEngineOutput:
    """Delegate to primary Laya decision engine (alias preserved for tool compatibility)."""
    return run_laya_decision(request)


@server.tool(structured_output=True)
def get_evaluation_metrics() -> EvaluationOutput:
    """Return saved offline evaluation metrics."""
    root = Path(__file__).resolve().parents[3]
    rows: list[dict[str, Any]] = []
    with (root / "reports" / "day3_evaluation_results.csv").open(
        newline="", encoding="utf-8"
    ) as file:
        rows = list(csv.DictReader(file))
    return EvaluationOutput(
        source="offline_saved_reports",
        recommendation_metrics=rows,
        ml_classification_metrics={},
    )


@server.tool(structured_output=True)
def save_decision(request: SaveDecisionInput) -> SaveDecisionOutput:
    """Persist a decision trace through the audit service."""
    payload = {
        "customer_id": request.customer_id,
        "status": "SUCCESS",
        "all_evaluated_candidates": [item.model_dump() for item in request.candidates],
        "recommendations": [item.model_dump() for item in request.candidates],
        "excluded_candidates": [],
        "decision_method": "WEIGHTED_DECISION",
    }
    with get_db_context() as session:
        decision_id = AuditService(session).log_decision_audit(payload)
    if decision_id is None:
        raise RuntimeError("Decision audit could not be persisted.")
    return SaveDecisionOutput(decision_id=decision_id, status="saved")


if __name__ == "__main__":
    server.run("stdio")
