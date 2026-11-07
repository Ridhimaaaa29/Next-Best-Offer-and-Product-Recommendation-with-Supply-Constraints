"""
Agent Explanation Generator (Placeholder).
Status: NOT YET IMPLEMENTED / PLANNED FOR FUTURE ITERATION.
This file is a placeholder conforming to the target project architecture.
"""

from typing import Dict, Any, List


class AgentExplanationService:
    """
    Placeholder for LLM-generated natural language offer explanations.
    Currently, deterministic score breakdowns and reason codes are generated directly
    by RecommendationModel.ScoreExplanation.
    """

    def __init__(self):
        pass

    def explain(self, recommendation: Dict[str, Any]) -> str:
        raise NotImplementedError(
            "Natural language agent explanation generation is planned for a future release. "
            "Use recommendation['score_explanation']['reason_codes']."
        )
