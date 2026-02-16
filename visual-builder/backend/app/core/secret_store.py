"""Encrypted secret storage with async support and multi-tenant isolation.

Phase -1 아키텍처 스파이크:
- asyncio.run() 버그 수정 -> async resolve() 메서드
- SECRET_KEY 환경변수 필수화 (자동생성 제거)
- 시크릿 이름 형식 검증
- 키 로테이션 지원 준비 (key_version)

M13 Multi-tenancy:
- owner_id column for per-user secret isolation
- Composite unique constraint on (name, owner_id)
- Admin can list all secrets; regular users see only their own
"""

from __future__ import annotations

import os
import re
from typing import Set

from cryptography.fernet import Fernet, MultiFernet

# 시크릿 이름 형식: 대문자로 시작, 대문자/숫자/언더스코어, 최대 64자
SECRET_NAME_PATTERN = re.compile(r'^[A-Z][A-Z0-9_]{0,63}$')


class SecretStoreError(Exception):
    """Secret store related errors."""
    pass


class SecretNotFoundError(SecretStoreError):
    """Secret not found."""
    def __init__(self, name: str) -> None:
        super().__init__(f"Secret '{name}' not found")
        self.name = name


class SecretNameInvalidError(SecretStoreError):
    """Invalid secret name format."""
    def __init__(self, name: str) -> None:
        super().__init__(
            f"Invalid secret name '{name}'. "
            "Must match pattern: ^[A-Z][A-Z0-9_]{{0,63}}$"
        )
        self.name = name


class SecretAccessDeniedError(SecretStoreError):
    """Secret access denied."""
    def __init__(self, name: str) -> None:
        super().__init__(f"Access denied for secret '{name}'")
        self.name = name


class SecretStore:
    """암호화된 시크릿 저장소 (async 지원).

    Features:
        - Fernet (AES-256) 암호화
        - SECRET_KEY 환경변수 필수
        - 시크릿 이름 형식 검증
        - 컨텍스트별 접근 제어 (화이트리스트)
        - 키 로테이션 준비 (key_version 필드)

    Example:
        >>> store = SecretStore(db)
        >>> await store.set("OPENAI_API_KEY", "sk-xxx")
        >>> value = await store.get("OPENAI_API_KEY")
        >>> resolved = await store.resolve("Bearer ${OPENAI_API_KEY}")
    """

    def __init__(self, db) -> None:
        """Initialize secret store.

        Args:
            db: Database connection/session.

        Raises:
            RuntimeError: If SECRET_KEY environment variable is not set.
        """
        self.db = db
        self._key = os.environ.get("SECRET_KEY")

        if not self._key:
            raise RuntimeError(
                "SECRET_KEY 환경변수가 필요합니다. "
                "생성 명령: python -c 'from cryptography.fernet import Fernet; "
                "print(Fernet.generate_key().decode())'"
            )

        try:
            key_bytes = (
                self._key.encode()
                if isinstance(self._key, str)
                else self._key
            )
            primary_fernet = Fernet(key_bytes)
        except Exception as e:
            raise RuntimeError(f"SECRET_KEY 형식 오류: {e}")

        # Support previous key for rotation period
        fernets = [primary_fernet]
        previous_key = os.environ.get("SECRET_KEY_PREVIOUS")
        if previous_key:
            try:
                prev_bytes = (
                    previous_key.encode()
                    if isinstance(previous_key, str)
                    else previous_key
                )
                fernets.append(Fernet(prev_bytes))
            except Exception:
                pass  # Ignore invalid previous key

        self._fernet = primary_fernet  # For encryption (always use current key)
        self._multi_fernet = MultiFernet(fernets)  # For decryption (tries all keys)

        # 현재 키 버전 (키 로테이션용)
        self._key_version = 1

    @staticmethod
    def validate_name(name: str) -> None:
        """Validate secret name format.

        Args:
            name: Secret name to validate.

        Raises:
            SecretNameInvalidError: If name format is invalid.
        """
        if not SECRET_NAME_PATTERN.match(name):
            raise SecretNameInvalidError(name)

    async def set(self, name: str, value: str, owner_id: str = "system") -> None:
        """Store encrypted secret scoped to an owner.

        Args:
            name: Secret name (must match pattern).
            value: Secret value to encrypt.
            owner_id: Owner user ID (default: "system" for backward compat).

        Raises:
            SecretNameInvalidError: If name format is invalid.
        """
        self.validate_name(name)

        encrypted = self._fernet.encrypt(value.encode())
        await self.db.execute(
            """INSERT INTO secrets (name, value, owner_id, key_version, created_at, updated_at)
               VALUES (:name, :value, :owner_id, :key_version, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
               ON CONFLICT(name, owner_id) DO UPDATE SET
               value = excluded.value,
               key_version = excluded.key_version,
               updated_at = CURRENT_TIMESTAMP""",
            {"name": name, "value": encrypted, "owner_id": owner_id, "key_version": self._key_version},
        )

    async def get(self, name: str, owner_id: str | None = None) -> str | None:
        """Get decrypted secret.

        Args:
            name: Secret name.
            owner_id: Owner user ID. None = match any owner (admin/system access).

        Returns:
            Decrypted value or None if not found.
        """
        if owner_id is not None:
            row = await self.db.fetchone(
                "SELECT value, key_version FROM secrets WHERE name = :name AND owner_id = :owner_id",
                {"name": name, "owner_id": owner_id},
            )
        else:
            row = await self.db.fetchone(
                "SELECT value, key_version FROM secrets WHERE name = :name",
                {"name": name},
            )
        if row:
            return self._multi_fernet.decrypt(row["value"]).decode()
        return None

    async def delete(self, name: str, owner_id: str | None = None) -> None:
        """Delete secret.

        Args:
            name: Secret name.
            owner_id: Owner user ID. None = match any owner (admin/system access).
        """
        if owner_id is not None:
            await self.db.execute(
                "DELETE FROM secrets WHERE name = :name AND owner_id = :owner_id",
                {"name": name, "owner_id": owner_id},
            )
        else:
            await self.db.execute(
                "DELETE FROM secrets WHERE name = :name",
                {"name": name},
            )

    async def list(self, owner_id: str | None = None) -> list[str]:
        """List secret names (not values).

        Args:
            owner_id: Owner user ID. None = list all secrets (admin access).

        Returns:
            List of secret names.
        """
        if owner_id is not None:
            rows = await self.db.fetchall(
                "SELECT name FROM secrets WHERE owner_id = :owner_id ORDER BY name",
                {"owner_id": owner_id},
            )
        else:
            rows = await self.db.fetchall("SELECT name FROM secrets ORDER BY name")
        return [row["name"] for row in rows]

    async def get_metadata(self, name: str, owner_id: str | None = None) -> dict | None:
        """Get secret metadata (timestamps, no value).

        Args:
            name: Secret name.
            owner_id: Owner user ID. None = match any owner (admin/system access).

        Returns:
            Metadata dict with name, created_at, updated_at or None if not found.
        """
        if owner_id is not None:
            row = await self.db.fetchone(
                "SELECT name, created_at, updated_at FROM secrets WHERE name = :name AND owner_id = :owner_id",
                {"name": name, "owner_id": owner_id},
            )
        else:
            row = await self.db.fetchone(
                "SELECT name, created_at, updated_at FROM secrets WHERE name = :name",
                {"name": name},
            )
        if row:
            return {"name": row["name"], "created_at": row["created_at"], "updated_at": row["updated_at"]}
        return None

    async def list_with_metadata(self, owner_id: str | None = None) -> list[dict]:
        """List secrets with metadata (no values).

        Args:
            owner_id: Owner user ID. None = list all secrets (admin access).

        Returns:
            List of metadata dicts with name, created_at, updated_at.
        """
        if owner_id is not None:
            rows = await self.db.fetchall(
                "SELECT name, created_at, updated_at FROM secrets WHERE owner_id = :owner_id ORDER BY name",
                {"owner_id": owner_id},
            )
        else:
            rows = await self.db.fetchall(
                "SELECT name, created_at, updated_at FROM secrets ORDER BY name"
            )
        return [{"name": row["name"], "created_at": row["created_at"], "updated_at": row["updated_at"]} for row in rows]

    async def resolve(
        self,
        text: str,
        allowed_secrets: Set[str] | None = None,
    ) -> str:
        """Resolve secret references in text.

        Replaces ${SECRET_NAME} patterns with actual secret values.
        This is the async version that fixes the asyncio.run() bug.

        Args:
            text: Text containing ${SECRET_NAME} references.
            allowed_secrets: Optional whitelist of allowed secret names.
                            If None, all secrets are allowed.

        Returns:
            Text with secrets resolved.

        Raises:
            SecretNameInvalidError: If secret name format is invalid.
            SecretAccessDeniedError: If secret is not in whitelist.
            SecretNotFoundError: If secret does not exist.
        """
        pattern = r'\$\{([^}]+)\}'
        matches = list(re.finditer(pattern, text))

        if not matches:
            return text

        result = text

        # Process in reverse order to maintain string positions
        for match in reversed(matches):
            name = match.group(1)

            # Validate secret name format
            if not SECRET_NAME_PATTERN.match(name):
                raise SecretNameInvalidError(name)

            # Check whitelist
            if allowed_secrets is not None and name not in allowed_secrets:
                raise SecretAccessDeniedError(name)

            # Get secret value
            value = await self.get(name)
            if value is None:
                raise SecretNotFoundError(name)

            # Replace in result
            result = result[:match.start()] + value + result[match.end():]

        return result

    async def rotate_key(self, new_key: bytes) -> int:
        """Rotate encryption key (re-encrypt all secrets).

        Args:
            new_key: New Fernet key.

        Returns:
            Number of secrets re-encrypted.
        """
        new_fernet = Fernet(new_key)
        new_version = self._key_version + 1

        # Get all secrets (all owners)
        rows = await self.db.fetchall(
            "SELECT name, value, key_version, owner_id FROM secrets"
        )

        count = 0
        for row in rows:
            # Decrypt with current key
            plaintext = self._multi_fernet.decrypt(row["value"])

            # Re-encrypt with new key
            new_ciphertext = new_fernet.encrypt(plaintext)

            # Update in database - use composite key (name, owner_id)
            await self.db.execute(
                """UPDATE secrets
                   SET value = :value, key_version = :key_version, updated_at = CURRENT_TIMESTAMP
                   WHERE name = :name AND owner_id = :owner_id""",
                {
                    "value": new_ciphertext,
                    "key_version": new_version,
                    "name": row["name"],
                    "owner_id": row["owner_id"],
                },
            )
            count += 1

        # Update instance to use new key
        old_fernet = self._fernet
        self._fernet = new_fernet
        self._key_version = new_version
        self._multi_fernet = MultiFernet([new_fernet, old_fernet])

        return count
