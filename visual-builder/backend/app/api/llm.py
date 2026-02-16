"""LLM provider management endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from ..auth import get_current_user
from ..auth.jwt import User
from ..config import get_settings
from ..core.rbac import require_permission

router = APIRouter(prefix="/api/llm", tags=["llm"])


class ProviderStatus(BaseModel):
    name: str = Field(..., description="Provider name")
    configured: bool = Field(..., description="Whether API key is set")
    models: list[str] = Field(..., description="Available models")


class ProvidersResponse(BaseModel):
    providers: list[ProviderStatus] = Field(..., description="Available LLM providers")
    default_model: str = Field(..., description="Default model", alias="defaultModel")

    model_config = {"populate_by_name": True}


class ModelInfo(BaseModel):
    id: str = Field(..., description="Model identifier")
    provider: str = Field(..., description="Provider name")
    display_name: str = Field(..., description="Human-readable name", alias="displayName")
    context_window: int = Field(..., description="Max context tokens", alias="contextWindow")
    cost_per_1k_input: float = Field(..., description="Cost per 1K input tokens", alias="costPer1kInput")
    cost_per_1k_output: float = Field(..., description="Cost per 1K output tokens", alias="costPer1kOutput")

    model_config = {"populate_by_name": True}


class ModelsResponse(BaseModel):
    models: list[ModelInfo] = Field(..., description="Available models")


OPENAI_MODELS = [
    ModelInfo(
        id="gpt-4o",
        provider="openai",
        display_name="GPT-4o",
        context_window=128000,
        cost_per_1k_input=0.0025,
        cost_per_1k_output=0.01,
    ),
    ModelInfo(
        id="gpt-4o-mini",
        provider="openai",
        display_name="GPT-4o Mini",
        context_window=128000,
        cost_per_1k_input=0.00015,
        cost_per_1k_output=0.0006,
    ),
    ModelInfo(
        id="gpt-4.1",
        provider="openai",
        display_name="GPT-4.1",
        context_window=1000000,
        cost_per_1k_input=0.002,
        cost_per_1k_output=0.008,
    ),
    ModelInfo(
        id="gpt-4.1-mini",
        provider="openai",
        display_name="GPT-4.1 Mini",
        context_window=1000000,
        cost_per_1k_input=0.0004,
        cost_per_1k_output=0.0016,
    ),
    ModelInfo(
        id="o1",
        provider="openai",
        display_name="O1",
        context_window=200000,
        cost_per_1k_input=0.015,
        cost_per_1k_output=0.06,
    ),
    ModelInfo(
        id="o1-mini",
        provider="openai",
        display_name="O1 Mini",
        context_window=128000,
        cost_per_1k_input=0.003,
        cost_per_1k_output=0.012,
    ),
]

ANTHROPIC_MODELS = [
    ModelInfo(
        id="claude-sonnet-4-5-20250929",
        provider="anthropic",
        display_name="Claude Sonnet 4.5",
        context_window=200000,
        cost_per_1k_input=0.003,
        cost_per_1k_output=0.015,
    ),
    ModelInfo(
        id="claude-haiku-4-5-20251001",
        provider="anthropic",
        display_name="Claude Haiku 4.5",
        context_window=200000,
        cost_per_1k_input=0.001,
        cost_per_1k_output=0.005,
    ),
    ModelInfo(
        id="claude-opus-4-6",
        provider="anthropic",
        display_name="Claude Opus 4.6",
        context_window=200000,
        cost_per_1k_input=0.005,
        cost_per_1k_output=0.025,
    ),
]

OLLAMA_MODELS = [
    ModelInfo(
        id="llama3.1",
        provider="ollama",
        display_name="Llama 3.1 (8B)",
        context_window=128000,
        cost_per_1k_input=0,
        cost_per_1k_output=0,
    ),
    ModelInfo(
        id="llama3.1:70b",
        provider="ollama",
        display_name="Llama 3.1 (70B)",
        context_window=128000,
        cost_per_1k_input=0,
        cost_per_1k_output=0,
    ),
    ModelInfo(
        id="mistral",
        provider="ollama",
        display_name="Mistral 7B",
        context_window=32000,
        cost_per_1k_input=0,
        cost_per_1k_output=0,
    ),
    ModelInfo(
        id="codellama",
        provider="ollama",
        display_name="Code Llama",
        context_window=16000,
        cost_per_1k_input=0,
        cost_per_1k_output=0,
    ),
]

GEMINI_MODELS = [
    ModelInfo(
        id="gemini-2.0-flash",
        provider="google",
        display_name="Gemini 2.0 Flash",
        context_window=1048576,
        cost_per_1k_input=0.0001,
        cost_per_1k_output=0.0004,
    ),
    ModelInfo(
        id="gemini-2.5-pro",
        provider="google",
        display_name="Gemini 2.5 Pro",
        context_window=1048576,
        cost_per_1k_input=0.00125,
        cost_per_1k_output=0.005,
    ),
]


@router.get("/providers", response_model=ProvidersResponse)
@require_permission("workflow:read")
async def list_providers(user: User = Depends(get_current_user)):
    """List available LLM providers and their configuration status."""
    settings = get_settings()

    providers = [
        ProviderStatus(
            name="openai",
            configured=bool(settings.openai_api_key),
            models=[m.id for m in OPENAI_MODELS],
        ),
        ProviderStatus(
            name="anthropic",
            configured=bool(settings.anthropic_api_key),
            models=[m.id for m in ANTHROPIC_MODELS],
        ),
        ProviderStatus(
            name="ollama",
            configured=True,  # Ollama doesn't need API key, just needs to be running
            models=[m.id for m in OLLAMA_MODELS],
        ),
        ProviderStatus(
            name="google",
            configured=bool(settings.gemini_api_key),
            models=[m.id for m in GEMINI_MODELS],
        ),
    ]

    return ProvidersResponse(
        providers=providers,
        default_model=settings.default_llm_model,
    )


@router.get("/models", response_model=ModelsResponse)
@require_permission("workflow:read")
async def list_models(user: User = Depends(get_current_user)):
    """List all available models with pricing and capabilities."""
    settings = get_settings()

    models = []
    if settings.openai_api_key:
        models.extend(OPENAI_MODELS)
    if settings.anthropic_api_key:
        models.extend(ANTHROPIC_MODELS)
    # Ollama is always available (no API key required)
    models.extend(OLLAMA_MODELS)
    if settings.gemini_api_key:
        models.extend(GEMINI_MODELS)

    if not models:
        models = OPENAI_MODELS + ANTHROPIC_MODELS + OLLAMA_MODELS + GEMINI_MODELS

    return ModelsResponse(models=models)
