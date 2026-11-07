"""Grounded Groq business assistant endpoints."""

from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from backend.app.config import settings

router = APIRouter(tags=["Assistant"])


class AssistantRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    context: dict[str, Any] = Field(default_factory=dict)


class AssistantResponse(BaseModel):
    provider: str
    configured: bool
    model: str | None
    answer: str
    disclaimer: str


def _groq_config() -> tuple[str | None, str]:
    return settings.groq_api_key, settings.groq_base_url


@router.get("/assistant/status")
async def assistant_status() -> dict[str, Any]:
    api_key, base_url = _groq_config()
    model = settings.groq_model
    if not api_key:
        return {"provider": "groq", "configured": False, "model": model, "model_verified": False}
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(
                f"{base_url.rstrip('/')}/models",
                headers={"Authorization": f"Bearer {api_key}"},
            )
        response.raise_for_status()
        models = {item["id"] for item in response.json().get("data", [])}
        return {
            "provider": "groq",
            "configured": True,
            "model": model,
            "model_verified": model in models,
        }
    except (httpx.HTTPError, ValueError, KeyError, TypeError):
        return {"provider": "groq", "configured": True, "model": model, "model_verified": False}


@router.post("/assistant/chat", response_model=AssistantResponse)
async def assistant_chat(request: AssistantRequest) -> AssistantResponse:
    api_key, base_url = _groq_config()
    model = settings.groq_model
    if not api_key:
        return AssistantResponse(
            provider="groq",
            configured=False,
            model=model,
            answer="Groq is not configured. Set GROQ_API_KEY and GROQ_MODEL on the backend.",
            disclaimer="No AI response was generated.",
        )
    system = (
        "You are the NBO Intelligence Assistant. Answer only from the supplied structured "
        "project context. Never invent inventory, margins, lead times, product relationships, "
        "or feasibility. If context is missing, say it is unavailable. Groq explanations "
        "are non-authoritative; deterministic policy results are authoritative. Do not execute actions."
    )
    payload = {
        "model": model,
        "temperature": 0.1,
        "messages": [
            {"role": "system", "content": system},
            {
                "role": "user",
                "content": f"Project context:\n{request.context}\n\nQuestion:\n{request.question}",
            },
        ],
    }
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{base_url.rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json=payload,
            )
        response.raise_for_status()
        data = response.json()
        answer = data["choices"][0]["message"]["content"]
    except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Configured Groq provider failed: {type(error).__name__}",
        ) from error
    return AssistantResponse(
        provider="groq",
        configured=True,
        model=model,
        answer=answer,
        disclaimer="Groq response is grounded in supplied context; policy decisions remain authoritative.",
    )
