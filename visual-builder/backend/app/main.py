"""Tool Hub Backend - FastAPI Application.

Architecture spike:
- Health check endpoints
- CORS configuration
- Security headers
- Error handling
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import get_settings
from app.logging_config import setup_logging
from app.core.rate_limiter import limiter

from .api import auth, webhooks, workflows, executions, mcp, secrets, schedules, debug_ws, versions, ab_tests, audit, users, llm, playground, documents

settings = get_settings()
logger = logging.getLogger(__name__)

# Application metadata
APP_TITLE = settings.app_name
APP_DESCRIPTION = "Visual Builder Workflow Engine Backend"
APP_VERSION = settings.app_version


class SQLAlchemyDBAdapter:
    """Adapter to bridge SQLAlchemy sessions with raw SQL interfaces.

    Used by ExecutionStateStore and SecretStore which expect
    a simple db.execute()/db.fetchone() interface.
    All queries must use named parameters (dict).
    """

    def __init__(self, session_factory) -> None:
        self._session_factory = session_factory

    async def execute(self, query: str, params: dict = None) -> None:
        from sqlalchemy import text
        async with self._session_factory() as session:
            await session.execute(text(query), params or {})
            await session.commit()

    async def fetchone(self, query: str, params: dict = None):
        from sqlalchemy import text
        async with self._session_factory() as session:
            result = await session.execute(text(query), params or {})
            row = result.fetchone()
            return dict(row._mapping) if row else None

    async def fetchall(self, query: str, params: dict = None):
        from sqlalchemy import text
        async with self._session_factory() as session:
            result = await session.execute(text(query), params or {})
            return [dict(row._mapping) for row in result.fetchall()]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan management."""
    # Configure logging first
    setup_logging()

    # Validate production secrets
    settings.validate_production_secrets()

    from app.core.scheduler import WorkflowScheduler
    from app.api.schedules import set_scheduler
    from app.db.database import get_session_factory, init_db

    # Startup
    logger.info("Starting %s v%s", APP_TITLE, APP_VERSION)

    # Initialize database
    await init_db()
    logger.info("Database initialized")

    session_factory = get_session_factory()
    db_adapter = SQLAlchemyDBAdapter(session_factory)

    # Initialize MCP Manager
    from app.core.mcp_manager import MCPManager
    mcp_manager = MCPManager()
    app.state.mcp_manager = mcp_manager
    logger.info("MCP Manager initialized")

    # Initialize SecretStore (auto-generate dev key if not set)
    if not os.environ.get("SECRET_KEY"):
        from cryptography.fernet import Fernet
        os.environ["SECRET_KEY"] = Fernet.generate_key().decode()
        logger.warning("Using auto-generated SECRET_KEY (dev mode only)")

    from app.core.secret_store import SecretStore
    secret_store = SecretStore(db_adapter)
    app.state.secret_store = secret_store

    # Initialize ExecutionStateStore + WorkflowExecutor
    from app.core.executor import ExecutionStateStore, WorkflowExecutor
    state_store = ExecutionStateStore(db_adapter)
    executor = WorkflowExecutor(mcp_manager, secret_store, state_store)
    app.state.executor = executor
    logger.info("WorkflowExecutor initialized")

    # Initialize BackgroundExecutionManager
    from app.core.background_executor import BackgroundExecutionManager
    bg_executor = BackgroundExecutionManager()
    app.state.bg_executor = bg_executor
    logger.info("BackgroundExecutionManager initialized")

    # Clean up stale executions from previous runs
    try:
        from sqlalchemy import text, update
        from app.models.execution import Execution as ExecutionModel
        async with session_factory() as session:
            result = await session.execute(
                update(ExecutionModel)
                .where(ExecutionModel.status == "running")
                .values(
                    status="failed",
                    error="Server restarted - execution was interrupted",
                )
            )
            if result.rowcount > 0:
                await session.commit()
                logger.warning("Marked %d stale 'running' executions as 'failed'", result.rowcount)
    except Exception:
        logger.warning("Failed to clean up stale executions", exc_info=True)

    # Initialize scheduler (only in primary worker for horizontal scaling)
    scheduler = WorkflowScheduler(executor, session_factory)
    set_scheduler(scheduler)

    # Scheduler singleton guard - only start in one worker when horizontally scaled
    if settings.scheduler_enabled:
        await scheduler.start()
        logger.info("Scheduler started (primary worker)")
    else:
        logger.info("Scheduler initialized but not started (secondary worker)")

    yield

    # Shutdown
    logger.info("Shutting down %s", APP_TITLE)

    # Shutdown background executor
    await bg_executor.shutdown()
    logger.info("BackgroundExecutionManager shutdown complete")

    # Shutdown scheduler (only if it was started)
    if settings.scheduler_enabled:
        await scheduler.shutdown()
        logger.info("Scheduler shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="Tool Hub API",
    description="""
## Visual Builder Workflow Engine

Tool Hub provides a visual workflow automation platform with:

- **Workflows**: Create and manage automation workflows with visual node-based editor
- **Executions**: Run workflows manually or on schedule with full execution tracking
- **MCP Integration**: Connect to 1000+ Model Context Protocol tool servers
- **Scheduling**: Cron-based automatic execution with run history
- **Debug Mode**: Step-through debugging with breakpoints and state inspection
- **Webhooks**: Trigger workflows via HTTP webhooks with signature verification
- **Versioning**: Track workflow changes and run specific versions
- **Audit Logging**: Full audit trail of all operations and modifications

### Authentication

All endpoints require JWT Bearer token authentication except health checks and webhooks.

```
Authorization: Bearer <your-jwt-token>
```

Generate tokens programmatically using the auth module.

### Rate Limits

- Workflow execution: 10 req/min
- Webhooks: 100 req/min (signature-based)
- General API: 1000 req/min per authenticated user
- Health checks: unlimited (public)

### Key Features

#### Workflow Execution Modes
- **Full Mode**: Execute with actual MCP server calls
- **Mock Mode**: Execute with simulated responses
- **Debug Mode**: Step-through debugging with breakpoints

#### Execution Tracking
- Real-time execution status and progress
- Per-node logs with input/output/duration
- Error details and retry information
- Resume capability from breakpoints

#### Security
- JWT authentication with role-based access control
- Secrets management with encrypted storage
- Webhook signature verification (HMAC-SHA256)
- Audit logging for compliance

### Getting Started

1. Generate a JWT token via your auth provider
2. Set Authorization header with Bearer token
3. POST to /api/workflows to create workflows
4. POST to /api/workflows/{id}/run to execute
5. GET /api/executions/{id} to check results

For interactive testing, access the Swagger UI at `/docs` or ReDoc at `/redoc`.
""",
    version=APP_VERSION,
    lifespan=lifespan,
    openapi_tags=[
        {
            "name": "workflows",
            "description": "Workflow CRUD operations - Create, read, update, and delete workflows. Manage workflow definitions with visual node-based structure.",
        },
        {
            "name": "executions",
            "description": "Workflow execution management - Run workflows, monitor execution status, stop/resume executions, retrieve logs and results.",
        },
        {
            "name": "schedules",
            "description": "Cron scheduling - Create and manage scheduled workflow executions. View run history and next scheduled times.",
        },
        {
            "name": "mcp",
            "description": "MCP server management - Connect to Model Context Protocol servers. List available tools and check server health.",
        },
        {
            "name": "secrets",
            "description": "Secret management - Securely store and manage API keys, credentials, and sensitive data for use in workflows.",
        },
        {
            "name": "versions",
            "description": "Workflow versioning - Track workflow changes, view version history, and execute specific workflow versions.",
        },
        {
            "name": "debug",
            "description": "Debug mode - Step-through debugging with breakpoints, state inspection, and execution replay.",
        },
        {
            "name": "health",
            "description": "Health checks - Liveness and readiness probes for monitoring and orchestration. MCP server health checks.",
        },
        {
            "name": "webhooks",
            "description": "Webhook management - Create incoming webhooks to trigger workflows from external systems with signature verification.",
        },
        {
            "name": "ab-tests",
            "description": "A/B Testing - Create and run A/B tests to compare workflow variants. Track metrics and export results.",
        },
        {
            "name": "llm",
            "description": "LLM provider management - View available AI models, check provider configuration status, and manage LLM settings.",
        },
        {
            "name": "playground",
            "description": "Playground chat interface - Execute workflows with chat-style interface and conversation history support.",
        },
    ],
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
    openapi_url="/openapi.json" if not settings.is_production else None,
)

# Rate limiter state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "Origin", "X-Requested-With"],
)


# Request body size limit middleware
MAX_BODY_SIZE = 10 * 1024 * 1024  # 10 MB

@app.middleware("http")
async def limit_request_body(request: Request, call_next):
    """Limit request body size to prevent memory exhaustion."""
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_BODY_SIZE:
        return JSONResponse(
            status_code=413,
            content={
                "error": {
                    "code": "PAYLOAD_TOO_LARGE",
                    "message": f"Request body exceeds maximum size of {MAX_BODY_SIZE // (1024 * 1024)}MB",
                }
            },
        )
    return await call_next(request)


# Security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Add security headers to all responses."""
    response = await call_next(request)

    # Security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: blob:; "
        "font-src 'self'; "
        "connect-src 'self' ws: wss:; "
        "frame-ancestors 'none'"
    )

    # HSTS in production
    if settings.is_production:
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )

    return response


# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with standard error format."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": f"HTTP_{exc.status_code}",
                "message": exc.detail if isinstance(exc.detail, str) else str(exc.detail),
            }
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions."""
    logger.exception("Unhandled exception")

    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
            }
        },
    )


# === Health Check Endpoints ===

@app.get("/health/live", tags=["health"])
async def health_live():
    """Liveness probe - process is running.

    Returns 200 if the process is alive.
    """
    return {"status": "alive"}


@app.get("/health/ready", tags=["health"])
async def health_ready():
    """Readiness probe - can accept work.

    Returns 200 if:
    - Database is connected
    - Scheduler is running
    - Redis is reachable (if configured)
    - Required services are available

    Note: Returns degraded status (not failure) if optional services are unavailable.
    """
    from app.api.schedules import get_scheduler
    from app.db.database import AsyncSessionLocal
    from sqlalchemy import text

    checks = {
        "database": False,
        "scheduler": False,
        "redis": None,  # None = not configured, True = healthy, False = unhealthy
    }

    # Check database connectivity
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        checks["database"] = True
    except Exception:
        checks["database"] = False

    # Check scheduler status
    try:
        scheduler = get_scheduler()
        checks["scheduler"] = scheduler.is_running
    except Exception:
        checks["scheduler"] = False

    # Check Redis connectivity (if configured)
    if settings.redis_url and settings.redis_url != "redis://localhost:6379/0":
        try:
            import redis.asyncio as aioredis
            redis_client = aioredis.from_url(settings.redis_url, decode_responses=True)
            await redis_client.ping()
            await redis_client.close()
            checks["redis"] = True
        except Exception:
            checks["redis"] = False
    else:
        # Redis not configured or using default placeholder
        checks["redis"] = None

    # Critical checks: database and scheduler must be healthy
    critical_healthy = checks["database"] and checks["scheduler"]
    # Redis is optional - degraded if configured but unhealthy
    degraded = checks["redis"] is False

    if critical_healthy and not degraded:
        status = "ready"
    elif critical_healthy and degraded:
        status = "degraded"
    else:
        status = "not_ready"

    return {
        "status": status,
        "checks": checks,
    }


@app.get("/health/mcp/{server_id}", tags=["health"])
async def health_mcp(server_id: str, request: Request):
    """MCP server health check.

    This endpoint is intentionally UNAUTHENTICATED for Kubernetes health check compatibility.
    K8s liveness/readiness probes do not support authentication headers, so this endpoint
    must remain publicly accessible. Security impact is minimal as it only exposes connection
    status (connected/disconnected) and tool count, not sensitive data.

    Args:
        server_id: MCP server ID to check.
        request: FastAPI request (provides access to app state).

    Returns:
        Server health status (connected/disconnected) and tools count.

    Security Note:
        - Intentionally no JWT authentication required
        - Safe for Kubernetes health probes
        - Only exposes non-sensitive health metadata
    """
    mcp_manager = request.app.state.mcp_manager

    if server_id not in mcp_manager._sessions:
        return {
            "server_id": server_id,
            "status": "disconnected",
            "message": "No active session for this server",
        }

    tools = mcp_manager._tools.get(server_id, [])
    return {
        "server_id": server_id,
        "status": "connected",
        "tools_count": len(tools),
    }


# === Include Routers ===

app.include_router(auth.router)
app.include_router(webhooks.router)
app.include_router(workflows.router)
app.include_router(executions.router)
app.include_router(mcp.router)
app.include_router(secrets.router)
app.include_router(schedules.router)
app.include_router(debug_ws.router)
app.include_router(versions.router)
app.include_router(ab_tests.router)
app.include_router(audit.router)
app.include_router(users.router)
app.include_router(llm.router)
app.include_router(playground.router)
app.include_router(documents.router)


# === Root Endpoint ===

@app.get("/", tags=["root"])
async def root():
    """API root endpoint."""
    return {
        "name": APP_TITLE,
        "version": APP_VERSION,
        "docs": "/docs",
        "health": "/health/live",
    }


# === Development Server ===

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.server_host,
        port=settings.server_port,
        reload=True,
    )
