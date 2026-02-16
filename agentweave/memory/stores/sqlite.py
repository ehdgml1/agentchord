"""SQLite-based memory storage."""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncIterator

from agentweave.memory.base import MemoryEntry
from agentweave.memory.stores.base import MemoryStore

# Optional dependency - gracefully handle missing aiosqlite
try:
    import aiosqlite

    AIOSQLITE_AVAILABLE = True
except ImportError:
    AIOSQLITE_AVAILABLE = False


class SQLiteStore(MemoryStore):
    """SQLite-based memory storage with async support.

    Stores entries in a SQLite database with the following schema:
        - id (TEXT PRIMARY KEY)
        - namespace (TEXT NOT NULL)
        - content (TEXT NOT NULL)
        - role (TEXT NOT NULL DEFAULT 'user')
        - timestamp (TEXT NOT NULL)
        - metadata (TEXT NOT NULL DEFAULT '{}')

    Supports both file-based and in-memory databases.

    Example:
        >>> store = SQLiteStore("memory.db")
        >>> await store.save("agent_1", entry)
        >>> entries = await store.load("agent_1")

    Note:
        Requires aiosqlite package: pip install aiosqlite
        For in-memory databases, the connection is kept open for the lifetime
        of the store instance.
    """

    def __init__(self, db_path: str | Path = ":memory:") -> None:
        """Initialize SQLite store.

        Args:
            db_path: Path to SQLite database file, or ":memory:" for in-memory DB.

        Raises:
            ImportError: If aiosqlite is not installed.
        """
        if not AIOSQLITE_AVAILABLE:
            raise ImportError(
                "aiosqlite is required for SQLiteStore. "
                "Install it with: pip install aiosqlite"
            )

        self._db_path = str(db_path)
        self._is_memory = self._db_path == ":memory:"
        self._memory_conn: aiosqlite.Connection | None = None
        self._table_created = False

    @asynccontextmanager
    async def _get_connection(self) -> AsyncIterator[aiosqlite.Connection]:
        """Get database connection.

        For :memory: databases, maintains a persistent connection.
        For file databases, creates a new connection per operation.
        """
        if self._is_memory:
            # Use persistent connection for :memory: databases
            if self._memory_conn is None:
                self._memory_conn = await aiosqlite.connect(self._db_path)
            yield self._memory_conn
        else:
            # Use new connection for file databases
            async with aiosqlite.connect(self._db_path) as db:
                yield db

    async def _ensure_table(self, db: aiosqlite.Connection) -> None:
        """Create table and indexes if they don't exist.

        Args:
            db: Active database connection.
        """
        if self._table_created and self._is_memory:
            # Skip if already created for memory database
            return

        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS memory_entries (
                id TEXT PRIMARY KEY,
                namespace TEXT NOT NULL,
                content TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user',
                timestamp TEXT NOT NULL,
                metadata TEXT NOT NULL DEFAULT '{}',
                UNIQUE(namespace, id)
            )
            """
        )

        await db.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_namespace
            ON memory_entries(namespace)
            """
        )

        await db.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_timestamp
            ON memory_entries(namespace, timestamp)
            """
        )

        await db.commit()
        self._table_created = True

    def _serialize_entry(self, entry: MemoryEntry) -> dict[str, Any]:
        """Serialize entry for database storage."""
        return {
            "id": entry.id,
            "content": entry.content,
            "role": entry.role,
            "timestamp": entry.timestamp.isoformat(),
            "metadata": json.dumps(entry.metadata),
        }

    def _deserialize_row(self, row: tuple[str, str, str, str, str]) -> MemoryEntry:
        """Deserialize database row to MemoryEntry."""
        id_, content, role, timestamp, metadata_json = row
        return MemoryEntry(
            id=id_,
            content=content,
            role=role,
            timestamp=timestamp,
            metadata=json.loads(metadata_json) if metadata_json else {},
        )

    async def save(self, namespace: str, entry: MemoryEntry) -> None:
        """Save a single entry."""
        data = self._serialize_entry(entry)

        async with self._get_connection() as db:
            await self._ensure_table(db)
            await db.execute(
                """
                INSERT INTO memory_entries (id, namespace, content, role, timestamp, metadata)
                VALUES (:id, :namespace, :content, :role, :timestamp, :metadata)
                ON CONFLICT(namespace, id) DO UPDATE SET
                    content = excluded.content,
                    role = excluded.role,
                    timestamp = excluded.timestamp,
                    metadata = excluded.metadata
                """,
                {**data, "namespace": namespace},
            )
            await db.commit()

    async def save_many(self, namespace: str, entries: list[MemoryEntry]) -> None:
        """Save multiple entries."""
        if not entries:
            return

        rows = [{**self._serialize_entry(e), "namespace": namespace} for e in entries]

        async with self._get_connection() as db:
            await self._ensure_table(db)
            # Atomic: clear + insert in a single transaction
            await db.execute(
                "DELETE FROM memory_entries WHERE namespace = ?",
                (namespace,),
            )
            await db.executemany(
                """
                INSERT OR REPLACE INTO memory_entries (id, namespace, content, role, timestamp, metadata)
                VALUES (:id, :namespace, :content, :role, :timestamp, :metadata)
                """,
                rows,
            )
            await db.commit()

    async def load(self, namespace: str) -> list[MemoryEntry]:
        """Load all entries for a namespace."""
        async with self._get_connection() as db:
            await self._ensure_table(db)
            async with db.execute(
                """
                SELECT id, content, role, timestamp, metadata
                FROM memory_entries
                WHERE namespace = ?
                ORDER BY timestamp ASC
                """,
                (namespace,),
            ) as cursor:
                rows = await cursor.fetchall()
                return [self._deserialize_row(row) for row in rows]

    async def delete(self, namespace: str, entry_id: str) -> bool:
        """Delete an entry by ID."""
        async with self._get_connection() as db:
            await self._ensure_table(db)
            cursor = await db.execute(
                """
                DELETE FROM memory_entries
                WHERE namespace = ? AND id = ?
                """,
                (namespace, entry_id),
            )
            await db.commit()
            return cursor.rowcount > 0

    async def clear(self, namespace: str) -> None:
        """Clear all entries for a namespace."""
        async with self._get_connection() as db:
            await self._ensure_table(db)
            await db.execute(
                "DELETE FROM memory_entries WHERE namespace = ?",
                (namespace,),
            )
            await db.commit()

    async def count(self, namespace: str) -> int:
        """Count entries in a namespace."""
        async with self._get_connection() as db:
            await self._ensure_table(db)
            async with db.execute(
                """
                SELECT COUNT(*)
                FROM memory_entries
                WHERE namespace = ?
                """,
                (namespace,),
            ) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else 0

    async def close(self) -> None:
        """Close the store and release resources.

        Important for :memory: databases to ensure proper cleanup.
        """
        if self._memory_conn is not None:
            await self._memory_conn.close()
            self._memory_conn = None
            self._table_created = False

    async def __aenter__(self) -> SQLiteStore:
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()
