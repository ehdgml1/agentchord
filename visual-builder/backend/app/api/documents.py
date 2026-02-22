"""Document file upload API endpoints for RAG."""
from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Request
from pydantic import BaseModel

from app.auth.jwt import User, get_current_user
from app.config import get_settings
from app.core.rate_limiter import limiter
from app.services.document_service import DocumentService, DocumentMeta, ALLOWED_EXTENSIONS

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/api/documents", tags=["documents"])


class DocumentMetaResponse(BaseModel):
    """Response model for document metadata."""
    id: str
    filename: str
    size: int
    mimeType: str
    createdAt: str


def _meta_to_response(meta: DocumentMeta) -> DocumentMetaResponse:
    return DocumentMetaResponse(
        id=meta.id,
        filename=meta.filename,
        size=meta.size,
        mimeType=meta.mime_type,
        createdAt=meta.created_at,
    )


def _get_doc_service() -> DocumentService:
    return DocumentService(settings.upload_dir)


@router.post("/upload", response_model=DocumentMetaResponse)
@limiter.limit("10/minute")
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
):
    """Upload a document file for RAG processing.

    Supported formats: .txt, .md, .csv, .pdf, .log, .json
    Max file size: 10MB (configurable)
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    doc_service = _get_doc_service()

    try:
        doc_service.validate_extension(file.filename)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    content = await file.read()

    try:
        meta = await doc_service.save_file(
            user_id=user.id,
            filename=file.filename,
            content=content,
            max_size_mb=settings.max_upload_size_mb,
        )
    except ValueError as e:
        raise HTTPException(status_code=413, detail=str(e))

    return _meta_to_response(meta)


@router.get("", response_model=list[DocumentMetaResponse])
@limiter.limit("60/minute")
async def list_documents(
    request: Request,
    user: User = Depends(get_current_user),
):
    """List all uploaded documents for the current user."""
    doc_service = _get_doc_service()
    files = doc_service.list_files(user.id)
    return [_meta_to_response(f) for f in files]


@router.delete("/{file_id}")
@limiter.limit("30/minute")
async def delete_document(
    request: Request,
    file_id: str,
    user: User = Depends(get_current_user),
):
    """Delete an uploaded document."""
    doc_service = _get_doc_service()
    try:
        await doc_service.delete_file(user.id, file_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Document not found")

    return {"status": "deleted"}
