"""LLM provider management endpoints."""
from __future__ import annotations

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from ..auth import get_current_user
from ..auth.jwt import User
from ..config import get_settings
from ..core.rate_limiter import limiter
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


class LLMKeyStatus(BaseModel):
    provider: str
    hasUserKey: bool = Field(..., alias="hasUserKey")
    hasServerKey: bool = Field(..., alias="hasServerKey")
    configured: bool

    model_config = {"populate_by_name": True}


class LLMKeyStatusResponse(BaseModel):
    keys: list[LLMKeyStatus]


class SetKeyRequest(BaseModel):
    apiKey: str = Field(..., alias="apiKey", min_length=1)

    model_config = {"populate_by_name": True}


class ValidateKeyRequest(BaseModel):
    apiKey: str = Field(..., alias="apiKey", min_length=1)

    model_config = {"populate_by_name": True}


class ValidateKeyResponse(BaseModel):
    valid: bool
    error: str | None = None


PROVIDER_SECRET_MAP = {
    "openai": "LLM_OPENAI_API_KEY",
    "anthropic": "LLM_ANTHROPIC_API_KEY",
    "google": "LLM_GEMINI_API_KEY",
    "ollama": "LLM_OLLAMA_BASE_URL",
}

VALID_PROVIDERS = set(PROVIDER_SECRET_MAP.keys())


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
async def list_providers(
    request: Request,
    user: User = Depends(get_current_user),
):
    """List available LLM providers and their configuration status."""
    settings = get_settings()
    secret_store = request.app.state.secret_store

    # Check user keys
    user_openai = False
    user_anthropic = False
    user_gemini = False
    try:
        user_openai = await secret_store.get("LLM_OPENAI_API_KEY", owner_id=user.id) is not None
        user_anthropic = await secret_store.get("LLM_ANTHROPIC_API_KEY", owner_id=user.id) is not None
        user_gemini = await secret_store.get("LLM_GEMINI_API_KEY", owner_id=user.id) is not None
    except Exception:
        pass

    providers = [
        ProviderStatus(
            name="openai",
            configured=bool(settings.openai_api_key) or user_openai,
            models=[m.id for m in OPENAI_MODELS],
        ),
        ProviderStatus(
            name="anthropic",
            configured=bool(settings.anthropic_api_key) or user_anthropic,
            models=[m.id for m in ANTHROPIC_MODELS],
        ),
        ProviderStatus(
            name="ollama",
            configured=True,
            models=[m.id for m in OLLAMA_MODELS],
        ),
        ProviderStatus(
            name="google",
            configured=bool(settings.gemini_api_key) or user_gemini,
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


@router.get("/keys", response_model=LLMKeyStatusResponse)
@limiter.limit("30/minute")
@require_permission("workflow:read")
async def get_key_status(
    request: Request,
    user: User = Depends(get_current_user),
):
    """Get API key status for all LLM providers."""
    settings = get_settings()
    secret_store = request.app.state.secret_store

    keys = []
    for provider, secret_name in PROVIDER_SECRET_MAP.items():
        # Check server env key
        if provider == "openai":
            has_server = bool(settings.openai_api_key)
        elif provider == "anthropic":
            has_server = bool(settings.anthropic_api_key)
        elif provider == "google":
            has_server = bool(settings.gemini_api_key)
        elif provider == "ollama":
            has_server = True  # Ollama doesn't need API key
        else:
            has_server = False

        # Check user DB key
        has_user = False
        try:
            user_key = await secret_store.get(secret_name, owner_id=user.id)
            has_user = user_key is not None
        except Exception:
            pass

        keys.append(LLMKeyStatus(
            provider=provider,
            hasUserKey=has_user,
            hasServerKey=has_server,
            configured=has_server or has_user,
        ))

    return LLMKeyStatusResponse(keys=keys)


@router.put("/keys/{provider}")
@limiter.limit("20/minute")
@require_permission("workflow:read")
async def set_key(
    provider: str,
    body: SetKeyRequest,
    request: Request,
    user: User = Depends(get_current_user),
):
    """Save a user API key for a provider."""
    if provider not in VALID_PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Invalid provider: {provider}")

    secret_name = PROVIDER_SECRET_MAP[provider]
    secret_store = request.app.state.secret_store

    await secret_store.set(secret_name, body.apiKey, owner_id=user.id)
    return {"status": "ok"}


@router.post("/keys/{provider}/validate", response_model=ValidateKeyResponse)
@limiter.limit("10/minute")
@require_permission("workflow:read")
async def validate_key(
    provider: str,
    body: ValidateKeyRequest,
    request: Request,
    user: User = Depends(get_current_user),
):
    """Validate an API key against the provider's API."""
    if provider not in VALID_PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Invalid provider: {provider}")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            if provider == "openai":
                resp = await client.get(
                    "https://api.openai.com/v1/models",
                    headers={"Authorization": f"Bearer {body.apiKey}"},
                )
                valid = resp.status_code == 200
                error = None if valid else "Invalid API key"
            elif provider == "anthropic":
                resp = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": body.apiKey,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    },
                    json={"model": "claude-haiku-4-5-20251001", "max_tokens": 1, "messages": [{"role": "user", "content": "hi"}]},
                )
                # 400 = valid key (bad request body is ok), 401 = invalid key
                valid = resp.status_code != 401
                error = None if valid else "Invalid API key"
            elif provider == "google":
                resp = await client.get(
                    f"https://generativelanguage.googleapis.com/v1beta/models?key={body.apiKey}",
                )
                valid = resp.status_code == 200
                error = None if valid else "Invalid API key"
            elif provider == "ollama":
                resp = await client.get(f"{body.apiKey.rstrip('/')}/api/tags")
                valid = resp.status_code == 200
                error = None if valid else "Cannot connect to Ollama"
            else:
                valid = False
                error = "Unknown provider"
    except httpx.ConnectError:
        valid = False
        error = "Connection failed. Check the URL/key."
    except Exception as e:
        valid = False
        error = str(e)

    return ValidateKeyResponse(valid=valid, error=error)


@router.delete("/keys/{provider}")
@limiter.limit("20/minute")
@require_permission("workflow:read")
async def delete_key(
    provider: str,
    request: Request,
    user: User = Depends(get_current_user),
):
    """Delete a user API key for a provider."""
    if provider not in VALID_PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Invalid provider: {provider}")

    secret_name = PROVIDER_SECRET_MAP[provider]
    secret_store = request.app.state.secret_store

    await secret_store.delete(secret_name, owner_id=user.id)
    return {"status": "ok"}
