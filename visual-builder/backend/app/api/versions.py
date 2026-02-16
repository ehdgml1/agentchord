"""Version API endpoints."""
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.auth import get_current_user
from app.auth.jwt import User
from app.core.rbac import require_permission, Role
from app.db.database import get_db
from app.core.version_store import WorkflowVersionStore
from app.repositories.workflow_repo import WorkflowRepository
from app.dtos.version import (
    VersionListResponse,
    VersionDetail,
    VersionCreateRequest,
    VersionRestoreResponse,
    VersionMetadata,
)
import json

router = APIRouter(
    prefix="/api/workflows/{workflow_id}/versions",
    tags=["versions"],
)


@router.get("", response_model=VersionListResponse)
@require_permission("workflow:read")
async def list_versions(
    workflow_id: str,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    """List workflow versions.

    Args:
        workflow_id: Workflow ID
        user: Current user
        session: Database session

    Returns:
        List of versions

    Raises:
        404: Workflow not found or user doesn't own it
    """
    workflow_repo = WorkflowRepository(session)
    workflow = await workflow_repo.get_by_id(workflow_id)

    if not workflow:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "code": "WORKFLOW_NOT_FOUND",
                    "message": f"Workflow '{workflow_id}' not found",
                }
            },
        )

    # Verify ownership (admins bypass this check)
    if user.role != Role.ADMIN and workflow.owner_id != user.id:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "code": "WORKFLOW_NOT_FOUND",
                    "message": f"Workflow '{workflow_id}' not found",
                }
            },
        )

    version_store = WorkflowVersionStore(session)
    versions = await version_store.list_versions(workflow_id)

    return VersionListResponse(
        versions=[VersionMetadata(**v) for v in versions],
        total=len(versions),
    )


@router.get("/{version_id}", response_model=VersionDetail)
@require_permission("workflow:read")
async def get_version(
    workflow_id: str,
    version_id: str,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    """Get specific version.

    Args:
        workflow_id: Workflow ID
        version_id: Version ID
        user: Current user
        session: Database session

    Returns:
        Version details

    Raises:
        404: Version not found or user doesn't own workflow
    """
    version_store = WorkflowVersionStore(session)
    version = await version_store.get_version(version_id)

    if not version or version["workflow_id"] != workflow_id:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "code": "VERSION_NOT_FOUND",
                    "message": f"Version '{version_id}' not found",
                }
            },
        )

    # Verify workflow ownership (admins bypass this check)
    if user.role != Role.ADMIN:
        workflow_repo = WorkflowRepository(session)
        workflow = await workflow_repo.get_by_id(workflow_id)
        if not workflow or workflow.owner_id != user.id:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": {
                        "code": "VERSION_NOT_FOUND",
                        "message": f"Version '{version_id}' not found",
                    }
                },
            )

    return VersionDetail(**version)


@router.post("", response_model=VersionMetadata, status_code=201)
@require_permission("workflow:write")
async def create_version(
    workflow_id: str,
    request: VersionCreateRequest,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    """Create workflow version.

    Args:
        workflow_id: Workflow ID
        request: Version creation request
        user: Current user
        session: Database session

    Returns:
        Created version metadata

    Raises:
        404: Workflow not found or user doesn't own it
    """
    workflow_repo = WorkflowRepository(session)
    workflow = await workflow_repo.get_by_id(workflow_id)

    if not workflow:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "code": "WORKFLOW_NOT_FOUND",
                    "message": f"Workflow '{workflow_id}' not found",
                }
            },
        )

    # Verify ownership (admins bypass this check)
    if user.role != Role.ADMIN and workflow.owner_id != user.id:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "code": "WORKFLOW_NOT_FOUND",
                    "message": f"Workflow '{workflow_id}' not found",
                }
            },
        )

    workflow_data = {
        "id": workflow.id,
        "name": workflow.name,
        "description": workflow.description,
        "nodes": json.loads(workflow.nodes),
        "edges": json.loads(workflow.edges),
        "status": workflow.status,
    }

    version_store = WorkflowVersionStore(session)
    version_id = await version_store.save_version(
        workflow_id,
        workflow_data,
        request.message,
    )

    await session.commit()

    version = await version_store.get_version(version_id)
    return VersionMetadata(
        id=version["id"],
        workflow_id=version["workflow_id"],
        version_number=version["version_number"],
        message=version["message"],
        created_at=version["created_at"],
    )


@router.post(
    "/{version_id}/restore",
    response_model=VersionRestoreResponse,
)
@require_permission("workflow:write")
async def restore_version(
    workflow_id: str,
    version_id: str,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    """Restore workflow to version.

    Args:
        workflow_id: Workflow ID
        version_id: Version ID to restore
        user: Current user
        session: Database session

    Returns:
        Restore confirmation

    Raises:
        404: Version not found or user doesn't own workflow
    """
    version_store = WorkflowVersionStore(session)

    try:
        restored_data = await version_store.restore_version(version_id)
    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "code": "VERSION_NOT_FOUND",
                    "message": str(e),
                }
            },
        )

    if restored_data.get("id") != workflow_id:
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "VERSION_MISMATCH",
                    "message": "Version does not belong to workflow",
                }
            },
        )

    workflow_repo = WorkflowRepository(session)
    workflow = await workflow_repo.get_by_id(workflow_id)

    if not workflow:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "code": "WORKFLOW_NOT_FOUND",
                    "message": f"Workflow '{workflow_id}' not found",
                }
            },
        )

    # Verify ownership (admins bypass this check) - CRITICAL for destructive operation
    if user.role != Role.ADMIN and workflow.owner_id != user.id:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "code": "WORKFLOW_NOT_FOUND",
                    "message": f"Workflow '{workflow_id}' not found",
                }
            },
        )

    workflow.name = restored_data.get("name", workflow.name)
    workflow.description = restored_data.get("description", workflow.description)
    workflow.nodes = json.dumps(restored_data.get("nodes", []))
    workflow.edges = json.dumps(restored_data.get("edges", []))
    workflow.status = restored_data.get("status", workflow.status)

    try:
        await workflow_repo.update(workflow)
        await session.commit()
    except Exception as e:
        await session.rollback()
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": "RESTORE_FAILED",
                    "message": f"Failed to apply restored version: {str(e)}",
                }
            },
        )

    version = await version_store.get_version(version_id)

    return VersionRestoreResponse(
        workflow_id=workflow_id,
        version_id=version_id,
        version_number=version["version_number"],
        message=f"Successfully restored to version {version['version_number']}",
    )
