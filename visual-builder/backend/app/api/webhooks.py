"""Webhook API with HMAC signature verification.

Phase -1 아키텍처 스파이크:
- HMAC 서명 검증 (SHA256)
- 리플레이 공격 방지 (타임스탬프 검증)
- IP 허용목록 지원
"""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import time
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.auth.jwt import User
from app.core.rbac import require_permission
from app.db.database import get_db
from app.repositories.webhook_repo import WebhookRepository
from app.repositories.workflow_repo import WorkflowRepository
from app.dtos.webhook import WebhookCreate, WebhookResponse, WebhookListResponse, WebhookSecretResponse
from app.models.webhook import Webhook as WebhookModel
from sqlalchemy import select


router = APIRouter(prefix="/webhook", tags=["webhooks"])


# Webhook signature header names
SIGNATURE_HEADER = "X-Webhook-Signature"
TIMESTAMP_HEADER = "X-Webhook-Timestamp"

# Replay attack prevention window (seconds)
TIMESTAMP_TOLERANCE = 300  # 5 minutes


class WebhookVerificationError(Exception):
    """Webhook verification failed."""
    pass


def verify_webhook_signature(
    body: bytes,
    signature: str,
    timestamp: str,
    secret: str,
) -> None:
    """Verify webhook HMAC signature.

    Args:
        body: Raw request body.
        signature: Signature from header (format: "sha256=<hmac>").
        timestamp: Unix timestamp from header.
        secret: Webhook secret for HMAC.

    Raises:
        WebhookVerificationError: If verification fails.
    """
    # Parse timestamp
    try:
        ts = int(timestamp)
    except ValueError:
        raise WebhookVerificationError("Invalid timestamp format")

    # Check timestamp is within tolerance (replay attack prevention)
    current_time = int(time.time())
    if abs(current_time - ts) > TIMESTAMP_TOLERANCE:
        raise WebhookVerificationError(
            f"Timestamp expired. Must be within {TIMESTAMP_TOLERANCE} seconds"
        )

    # Parse signature
    if not signature.startswith("sha256="):
        raise WebhookVerificationError(
            "Invalid signature format. Expected: sha256=<hmac>"
        )
    provided_hmac = signature[7:]  # Remove "sha256=" prefix

    # Compute expected signature
    # Payload format: "{timestamp}.{body}"
    payload = f"{timestamp}.{body.decode('utf-8')}"
    expected_hmac = hmac.new(
        secret.encode(),
        payload.encode(),
        hashlib.sha256,
    ).hexdigest()

    # Constant-time comparison to prevent timing attacks
    if not hmac.compare_digest(provided_hmac, expected_hmac):
        raise WebhookVerificationError("Invalid signature")


def verify_ip_allowlist(client_ip: str, allowed_ips: str | None) -> None:
    """Verify client IP is in allowlist.

    Args:
        client_ip: Client IP address.
        allowed_ips: Comma-separated list of allowed IPs, or None for any.

    Raises:
        WebhookVerificationError: If IP not allowed.
    """
    if not allowed_ips:
        return  # No restriction

    allowed_list = [ip.strip() for ip in allowed_ips.split(",")]
    if client_ip not in allowed_list:
        raise WebhookVerificationError(
            f"IP {client_ip} not in allowlist"
        )




@router.post("/{webhook_id}")
async def handle_webhook(
    webhook_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Handle incoming webhook request.

    Headers:
        X-Webhook-Signature: sha256=<hmac>
        X-Webhook-Timestamp: <unix_timestamp>

    Request body:
        JSON payload to pass as workflow input.

    Returns:
        execution_id: ID of started execution.
        status: Execution status.

    Raises:
        401: Signature verification failed.
        403: IP not allowed.
        404: Webhook not found.
        400: Webhook disabled or invalid payload.
    """
    # Get raw body
    body = await request.body()

    # Get headers
    signature = request.headers.get(SIGNATURE_HEADER)
    timestamp = request.headers.get(TIMESTAMP_HEADER)

    if not signature or not timestamp:
        raise HTTPException(
            status_code=401,
            detail={
                "error": {
                    "code": "WEBHOOK_HEADERS_MISSING",
                    "message": f"Missing required headers: {SIGNATURE_HEADER}, {TIMESTAMP_HEADER}",
                }
            },
        )

    # Get webhook config from database
    repo = WebhookRepository(db)
    webhook_model = await repo.get_by_id(webhook_id)

    if not webhook_model:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "code": "WEBHOOK_NOT_FOUND",
                    "message": f"Webhook '{webhook_id}' not found",
                }
            },
        )

    # Check if webhook is enabled
    if not webhook_model.enabled:
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "WEBHOOK_DISABLED",
                    "message": "Webhook is disabled",
                }
            },
        )

    # Verify IP allowlist
    client_ip = request.client.host if request.client else "unknown"
    try:
        verify_ip_allowlist(client_ip, webhook_model.allowed_ips)
    except WebhookVerificationError as e:
        raise HTTPException(
            status_code=403,
            detail={
                "error": {
                    "code": "WEBHOOK_IP_NOT_ALLOWED",
                    "message": str(e),
                }
            },
        )

    # Verify signature
    try:
        verify_webhook_signature(
            body=body,
            signature=signature,
            timestamp=timestamp,
            secret=webhook_model.secret,
        )
    except WebhookVerificationError as e:
        raise HTTPException(
            status_code=401,
            detail={
                "error": {
                    "code": "WEBHOOK_SIGNATURE_INVALID",
                    "message": str(e),
                }
            },
        )

    # Parse body
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "WEBHOOK_PAYLOAD_INVALID",
                    "message": "Invalid JSON payload",
                }
            },
        )

    # Execute workflow
    from app.repositories.workflow_repo import WorkflowRepository
    from app.repositories.execution_repo import ExecutionRepository
    from app.services.execution_service import ExecutionService
    from app.core.executor import ExecutionStateStore

    workflow_repo = WorkflowRepository(db)
    execution_repo = ExecutionRepository(db)
    executor = request.app.state.executor
    state_store = executor.state_store
    execution_service = ExecutionService(executor, execution_repo, workflow_repo, state_store)

    execution = await execution_service.start_execution(
        workflow_id=webhook_model.workflow_id,
        input=json.dumps(payload),
        mode="full",
        trigger_type="webhook",
        trigger_id=webhook_id,
    )
    await db.commit()

    # Update last_called_at
    await repo.update_last_called(webhook_id, datetime.now(UTC).replace(tzinfo=None))
    await db.commit()

    return {
        "execution_id": execution.id,
        "status": execution.status,
    }


# === Webhook Management API ===

@router.get("")
@require_permission("workflow:read")
async def list_webhooks(
    user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """List webhooks owned by current user."""
    from app.models.workflow import Workflow as WorkflowModel

    # Join webhooks with workflows to filter by owner
    stmt = (
        select(WebhookModel)
        .join(WorkflowModel, WebhookModel.workflow_id == WorkflowModel.id)
        .where(WorkflowModel.owner_id == user.id)
        .order_by(WebhookModel.created_at.desc())
    )
    result = await db.execute(stmt)
    webhooks = list(result.scalars().all())

    return WebhookListResponse(
        webhooks=[
            WebhookResponse(
                id=w.id,
                workflow_id=w.workflow_id,
                allowed_ips=w.allowed_ips,
                input_mapping=w.input_mapping,
                enabled=w.enabled,
                last_called_at=w.last_called_at.isoformat() if w.last_called_at else None,
                created_at=w.created_at.isoformat(),
            )
            for w in webhooks
        ],
        total=len(webhooks),
    )


@router.post("", response_model=WebhookResponse, status_code=201)
@require_permission("workflow:write")
async def create_webhook(
    data: WebhookCreate,
    user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """Create new webhook."""
    # Verify user owns the workflow
    workflow_repo = WorkflowRepository(db)
    workflow = await workflow_repo.get_by_id(data.workflow_id)

    if not workflow:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "code": "WORKFLOW_NOT_FOUND",
                    "message": f"Workflow '{data.workflow_id}' not found",
                }
            },
        )

    if workflow.owner_id and workflow.owner_id != user.id:
        raise HTTPException(
            status_code=403,
            detail={
                "error": {
                    "code": "ACCESS_DENIED",
                    "message": "You do not have access to this workflow",
                }
            },
        )

    repo = WebhookRepository(db)
    webhook_secret = secrets.token_hex(32)
    webhook = await repo.create(
        workflow_id=data.workflow_id,
        secret=webhook_secret,
        allowed_ips=data.allowed_ips,
        input_mapping=data.input_mapping,
    )
    await db.commit()
    return WebhookResponse(
        id=webhook.id,
        workflow_id=webhook.workflow_id,
        allowed_ips=webhook.allowed_ips,
        input_mapping=webhook.input_mapping,
        enabled=webhook.enabled,
        last_called_at=None,
        created_at=webhook.created_at.isoformat(),
    )


@router.get("/{webhook_id}", response_model=WebhookResponse)
@require_permission("workflow:read")
async def get_webhook(
    webhook_id: str,
    user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """Get webhook details (without secret)."""
    repo = WebhookRepository(db)
    webhook = await repo.get_by_id(webhook_id)
    if not webhook:
        raise HTTPException(404, {"error": {"code": "NOT_FOUND", "message": f"Webhook '{webhook_id}' not found"}})

    # Verify user owns the associated workflow
    workflow_repo = WorkflowRepository(db)
    workflow = await workflow_repo.get_by_id(webhook.workflow_id)

    if not workflow:
        # Webhook exists but workflow is gone - return 404 to avoid information leakage
        raise HTTPException(404, {"error": {"code": "NOT_FOUND", "message": f"Webhook '{webhook_id}' not found"}})

    if workflow.owner_id and workflow.owner_id != user.id:
        # Return 404 instead of 403 to prevent enumeration attacks
        raise HTTPException(404, {"error": {"code": "NOT_FOUND", "message": f"Webhook '{webhook_id}' not found"}})

    return WebhookResponse(
        id=webhook.id,
        workflow_id=webhook.workflow_id,
        allowed_ips=webhook.allowed_ips,
        input_mapping=webhook.input_mapping,
        enabled=webhook.enabled,
        last_called_at=webhook.last_called_at.isoformat() if webhook.last_called_at else None,
        created_at=webhook.created_at.isoformat(),
    )


@router.delete("/{webhook_id}", status_code=204)
@require_permission("workflow:write")
async def delete_webhook(
    webhook_id: str,
    user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """Delete webhook."""
    repo = WebhookRepository(db)
    webhook = await repo.get_by_id(webhook_id)
    if not webhook:
        raise HTTPException(404, {"error": {"code": "NOT_FOUND", "message": f"Webhook '{webhook_id}' not found"}})

    # Verify user owns the associated workflow
    workflow_repo = WorkflowRepository(db)
    workflow = await workflow_repo.get_by_id(webhook.workflow_id)

    if not workflow:
        # Webhook exists but workflow is gone - return 404
        raise HTTPException(404, {"error": {"code": "NOT_FOUND", "message": f"Webhook '{webhook_id}' not found"}})

    if workflow.owner_id and workflow.owner_id != user.id:
        # Return 404 instead of 403 to prevent enumeration attacks
        raise HTTPException(404, {"error": {"code": "NOT_FOUND", "message": f"Webhook '{webhook_id}' not found"}})

    deleted = await repo.delete(webhook_id)
    if not deleted:
        raise HTTPException(404, {"error": {"code": "NOT_FOUND", "message": f"Webhook '{webhook_id}' not found"}})
    await db.commit()


@router.post("/{webhook_id}/rotate", response_model=WebhookSecretResponse)
@require_permission("workflow:write")
async def rotate_webhook_secret(
    webhook_id: str,
    user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """Rotate webhook secret."""
    repo = WebhookRepository(db)
    webhook = await repo.get_by_id(webhook_id)
    if not webhook:
        raise HTTPException(404, {"error": {"code": "NOT_FOUND", "message": f"Webhook '{webhook_id}' not found"}})

    # Verify user owns the associated workflow
    workflow_repo = WorkflowRepository(db)
    workflow = await workflow_repo.get_by_id(webhook.workflow_id)

    if not workflow:
        # Webhook exists but workflow is gone - return 404
        raise HTTPException(404, {"error": {"code": "NOT_FOUND", "message": f"Webhook '{webhook_id}' not found"}})

    if workflow.owner_id and workflow.owner_id != user.id:
        # Return 404 instead of 403 to prevent enumeration attacks
        raise HTTPException(404, {"error": {"code": "NOT_FOUND", "message": f"Webhook '{webhook_id}' not found"}})

    new_secret = secrets.token_hex(32)
    webhook = await repo.rotate_secret(webhook_id, new_secret)
    if not webhook:
        raise HTTPException(404, {"error": {"code": "NOT_FOUND", "message": f"Webhook '{webhook_id}' not found"}})
    await db.commit()
    return WebhookSecretResponse(id=webhook.id, secret=new_secret)
