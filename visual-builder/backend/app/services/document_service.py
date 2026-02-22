"""Document file management service for RAG uploads."""
from __future__ import annotations

import asyncio
import json
import logging
import os
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime, UTC
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {".txt", ".md", ".csv", ".pdf", ".log", ".json"}
MAX_NODE_TOTAL_MB = 50


@dataclass
class DocumentMeta:
    """Metadata for an uploaded document file."""
    id: str
    filename: str
    size: int
    mime_type: str
    created_at: str


class DocumentService:
    """Manages uploaded document files for RAG nodes.

    Files are stored at: {base_dir}/{user_id}/{file_id}{ext}
    Metadata is stored at: {base_dir}/{user_id}/_meta.json
    """

    _user_locks: dict[str, asyncio.Lock] = {}

    def __init__(self, base_dir: str) -> None:
        self._base_dir = Path(base_dir)

    @staticmethod
    def _validate_file_id(file_id: str) -> None:
        """Validate file_id is alphanumeric to prevent path traversal."""
        if not file_id.isalnum():
            raise ValueError(f"Invalid file ID: {file_id}")

    def _get_user_lock(self, user_id: str) -> asyncio.Lock:
        """Get or create a lock for a specific user."""
        if user_id not in self._user_locks:
            self._user_locks[user_id] = asyncio.Lock()
        return self._user_locks[user_id]

    def _user_dir(self, user_id: str) -> Path:
        """Get user's upload directory, preventing path traversal."""
        safe_id = user_id.replace("/", "_").replace("..", "_")
        return self._base_dir / safe_id

    def _meta_path(self, user_id: str) -> Path:
        return self._user_dir(user_id) / "_meta.json"

    def _load_meta(self, user_id: str) -> list[dict[str, Any]]:
        meta_path = self._meta_path(user_id)
        if not meta_path.exists():
            return []
        try:
            return json.loads(meta_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return []

    def _save_meta(self, user_id: str, entries: list[dict[str, Any]]) -> None:
        meta_path = self._meta_path(user_id)
        meta_path.parent.mkdir(parents=True, exist_ok=True)
        meta_path.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")

    @staticmethod
    def _get_mime_type(ext: str) -> str:
        mime_map = {
            ".txt": "text/plain",
            ".md": "text/markdown",
            ".csv": "text/csv",
            ".pdf": "application/pdf",
            ".log": "text/plain",
            ".json": "application/json",
        }
        return mime_map.get(ext, "application/octet-stream")

    @staticmethod
    def validate_extension(filename: str) -> str:
        """Validate and return the file extension. Raises ValueError if not allowed."""
        ext = Path(filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise ValueError(
                f"File type '{ext}' not allowed. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
            )
        return ext

    async def save_file(
        self, user_id: str, filename: str, content: bytes, max_size_mb: int = 10
    ) -> DocumentMeta:
        """Save an uploaded file and return its metadata.

        Args:
            user_id: Owner user ID.
            filename: Original filename.
            content: File bytes.
            max_size_mb: Maximum file size in MB.

        Returns:
            DocumentMeta with file information.

        Raises:
            ValueError: If file extension not allowed or size exceeded.
        """
        ext = self.validate_extension(filename)

        size = len(content)
        if size > max_size_mb * 1024 * 1024:
            raise ValueError(f"File size {size} bytes exceeds limit of {max_size_mb}MB")

        # Validate PDF magic byte
        if ext == ".pdf" and not content[:5].startswith(b"%PDF-"):
            raise ValueError("File does not appear to be a valid PDF")

        async with self._get_user_lock(user_id):
            # Check total size for this user
            entries = self._load_meta(user_id)
            total_existing = sum(e.get("size", 0) for e in entries)
            if total_existing + size > MAX_NODE_TOTAL_MB * 1024 * 1024:
                raise ValueError(f"Total upload size would exceed {MAX_NODE_TOTAL_MB}MB limit")

            file_id = uuid.uuid4().hex[:12]
            user_dir = self._user_dir(user_id)
            user_dir.mkdir(parents=True, exist_ok=True)

            file_path = user_dir / f"{file_id}{ext}"
            await asyncio.to_thread(file_path.write_bytes, content)

            meta = DocumentMeta(
                id=file_id,
                filename=filename,
                size=size,
                mime_type=self._get_mime_type(ext),
                created_at=datetime.now(UTC).isoformat(),
            )

            entries.append(asdict(meta))
            self._save_meta(user_id, entries)

        logger.info("Saved document %s for user %s (%d bytes)", file_id, user_id, size)
        return meta

    def list_files(self, user_id: str) -> list[DocumentMeta]:
        """List all uploaded files for a user."""
        entries = self._load_meta(user_id)
        return [DocumentMeta(**e) for e in entries]

    def get_file_path(self, user_id: str, file_id: str) -> Path:
        """Get the filesystem path for a specific file.

        Raises:
            FileNotFoundError: If file not found.
            ValueError: If file_id is invalid.
        """
        self._validate_file_id(file_id)
        entries = self._load_meta(user_id)
        meta_entry = next((e for e in entries if e["id"] == file_id), None)
        if not meta_entry:
            raise FileNotFoundError(f"Document {file_id} not found")

        ext = Path(meta_entry["filename"]).suffix.lower()
        file_path = self._user_dir(user_id) / f"{file_id}{ext}"
        if not file_path.exists():
            raise FileNotFoundError(f"Document file {file_id} not found on disk")

        return file_path

    async def delete_file(self, user_id: str, file_id: str) -> None:
        """Delete a file and its metadata.

        Raises:
            FileNotFoundError: If file not found.
            ValueError: If file_id is invalid.
        """
        self._validate_file_id(file_id)

        async with self._get_user_lock(user_id):
            entries = self._load_meta(user_id)
            meta_entry = next((e for e in entries if e["id"] == file_id), None)
            if not meta_entry:
                raise FileNotFoundError(f"Document {file_id} not found")

            ext = Path(meta_entry["filename"]).suffix.lower()
            file_path = self._user_dir(user_id) / f"{file_id}{ext}"
            if file_path.exists():
                file_path.unlink()

            entries = [e for e in entries if e["id"] != file_id]
            self._save_meta(user_id, entries)

        logger.info("Deleted document %s for user %s", file_id, user_id)

    async def load_as_documents(self, user_id: str, file_id: str) -> list:
        """Load a file as agentchord Document objects using appropriate loader.

        Returns:
            List of agentchord Document objects.

        Raises:
            FileNotFoundError: If file not found.
        """
        from agentchord.rag.types import Document

        file_path = self.get_file_path(user_id, file_id)
        ext = file_path.suffix.lower()

        if ext == ".pdf":
            try:
                from agentchord.rag.loaders.pdf import PDFLoader
                loader = PDFLoader(str(file_path))
                return await loader.load()
            except ImportError:
                logger.warning("PDFLoader not available, reading as text")
                content = file_path.read_text(encoding="utf-8", errors="replace")
                return [Document(id=f"file-{file_id}", content=content, metadata={"source": str(file_path), "filename": file_path.name})]
        else:
            # .txt, .md, .csv, .log, .json all read as text
            try:
                from agentchord.rag.loaders.text import TextLoader
                loader = TextLoader(str(file_path))
                return await loader.load()
            except ImportError:
                content = file_path.read_text(encoding="utf-8", errors="replace")
                return [Document(id=f"file-{file_id}", content=content, metadata={"source": str(file_path), "filename": file_path.name})]
