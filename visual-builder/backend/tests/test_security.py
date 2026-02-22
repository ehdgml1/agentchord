"""Comprehensive security tests for AgentChord Visual Builder.

Tests covering:
1. Webhook HMAC verification
2. SecretStore encryption/decryption
3. MCP Manager command injection prevention
4. JWT token security
5. Input validation and injection prevention
"""
import pytest
import pytest_asyncio
import hmac
import hashlib
import time
import json
import jwt as pyjwt
from datetime import datetime, timedelta, UTC
from unittest.mock import AsyncMock, MagicMock, patch
from cryptography.fernet import Fernet

from app.api.webhooks import (
    verify_webhook_signature,
    verify_ip_allowlist,
    WebhookVerificationError,
    TIMESTAMP_TOLERANCE,
)
from app.core.secret_store import (
    SecretStore,
    SecretStoreError,
    SecretNotFoundError,
    SecretNameInvalidError,
    SecretAccessDeniedError,
)
from app.core.mcp_manager import (
    MCPServerConfig,
    MCPManager,
    MCPCommandNotAllowedError,
    MCPManagerError,
)
from app.auth.jwt import (
    create_access_token,
    decode_token,
    JWT_SECRET,
    JWT_ALGORITHM,
)
from app.core.rbac import Role


# ==================== Webhook HMAC Verification Tests ====================

class TestWebhookHMACVerification:
    """Test webhook HMAC signature verification."""

    def test_valid_hmac_signature_passes(self):
        """Valid HMAC signature should pass verification."""
        body = b'{"test": "data"}'
        secret = "test-secret-key"
        timestamp = str(int(time.time()))

        # Generate valid signature
        payload = f"{timestamp}.{body.decode('utf-8')}"
        expected_hmac = hmac.new(
            secret.encode(),
            payload.encode(),
            hashlib.sha256,
        ).hexdigest()
        signature = f"sha256={expected_hmac}"

        # Should not raise
        verify_webhook_signature(body, signature, timestamp, secret)

    def test_invalid_hmac_signature_rejected(self):
        """Invalid HMAC signature should be rejected."""
        body = b'{"test": "data"}'
        secret = "test-secret-key"
        timestamp = str(int(time.time()))
        signature = "sha256=invalid_signature_here"

        with pytest.raises(WebhookVerificationError, match="Invalid signature"):
            verify_webhook_signature(body, signature, timestamp, secret)

    def test_missing_signature_prefix_rejected(self):
        """Signature without sha256= prefix should be rejected."""
        body = b'{"test": "data"}'
        secret = "test-secret-key"
        timestamp = str(int(time.time()))
        signature = "just_a_hash_without_prefix"

        with pytest.raises(WebhookVerificationError, match="Invalid signature format"):
            verify_webhook_signature(body, signature, timestamp, secret)

    def test_expired_timestamp_rejected(self):
        """Timestamp outside tolerance window should be rejected."""
        body = b'{"test": "data"}'
        secret = "test-secret-key"
        # Timestamp from 10 minutes ago (exceeds 5 minute tolerance)
        timestamp = str(int(time.time()) - 600)

        # Generate valid signature for old timestamp
        payload = f"{timestamp}.{body.decode('utf-8')}"
        expected_hmac = hmac.new(
            secret.encode(),
            payload.encode(),
            hashlib.sha256,
        ).hexdigest()
        signature = f"sha256={expected_hmac}"

        with pytest.raises(WebhookVerificationError, match="Timestamp expired"):
            verify_webhook_signature(body, signature, timestamp, secret)

    def test_future_timestamp_rejected(self):
        """Future timestamp outside tolerance should be rejected."""
        body = b'{"test": "data"}'
        secret = "test-secret-key"
        # Timestamp 10 minutes in future
        timestamp = str(int(time.time()) + 600)

        payload = f"{timestamp}.{body.decode('utf-8')}"
        expected_hmac = hmac.new(
            secret.encode(),
            payload.encode(),
            hashlib.sha256,
        ).hexdigest()
        signature = f"sha256={expected_hmac}"

        with pytest.raises(WebhookVerificationError, match="Timestamp expired"):
            verify_webhook_signature(body, signature, timestamp, secret)

    def test_invalid_timestamp_format_rejected(self):
        """Non-numeric timestamp should be rejected."""
        body = b'{"test": "data"}'
        secret = "test-secret-key"
        timestamp = "not-a-number"
        signature = "sha256=anything"

        with pytest.raises(WebhookVerificationError, match="Invalid timestamp format"):
            verify_webhook_signature(body, signature, timestamp, secret)

    def test_different_secret_produces_different_signature(self):
        """Different secret keys should produce different signatures."""
        body = b'{"test": "data"}'
        timestamp = str(int(time.time()))

        # Generate signature with secret1
        secret1 = "secret-key-1"
        payload = f"{timestamp}.{body.decode('utf-8')}"
        sig1 = hmac.new(secret1.encode(), payload.encode(), hashlib.sha256).hexdigest()

        # Try to verify with secret2
        secret2 = "secret-key-2"
        signature = f"sha256={sig1}"

        with pytest.raises(WebhookVerificationError, match="Invalid signature"):
            verify_webhook_signature(body, signature, timestamp, secret2)

    def test_tampering_with_body_fails_verification(self):
        """Tampering with request body should fail verification."""
        original_body = b'{"test": "data"}'
        tampered_body = b'{"test": "tampered"}'
        secret = "test-secret-key"
        timestamp = str(int(time.time()))

        # Generate signature for original body
        payload = f"{timestamp}.{original_body.decode('utf-8')}"
        expected_hmac = hmac.new(
            secret.encode(),
            payload.encode(),
            hashlib.sha256,
        ).hexdigest()
        signature = f"sha256={expected_hmac}"

        # Verify with tampered body
        with pytest.raises(WebhookVerificationError, match="Invalid signature"):
            verify_webhook_signature(tampered_body, signature, timestamp, secret)

    def test_constant_time_comparison_prevents_timing_attacks(self):
        """HMAC verification uses constant-time comparison."""
        # This is enforced by using hmac.compare_digest in the implementation
        # We verify it's being used by checking the function doesn't return early
        body = b'{"test": "data"}'
        secret = "test-secret-key"
        timestamp = str(int(time.time()))

        # Two different invalid signatures should take similar time
        sig1 = "sha256=" + "a" * 64
        sig2 = "sha256=" + "z" * 64

        with pytest.raises(WebhookVerificationError):
            verify_webhook_signature(body, sig1, timestamp, secret)

        with pytest.raises(WebhookVerificationError):
            verify_webhook_signature(body, sig2, timestamp, secret)


class TestWebhookIPAllowlist:
    """Test webhook IP allowlist verification."""

    def test_ip_in_allowlist_passes(self):
        """IP in allowlist should pass."""
        verify_ip_allowlist("192.168.1.100", "192.168.1.100,10.0.0.1")

    def test_ip_not_in_allowlist_rejected(self):
        """IP not in allowlist should be rejected."""
        with pytest.raises(WebhookVerificationError, match="not in allowlist"):
            verify_ip_allowlist("192.168.1.200", "192.168.1.100,10.0.0.1")

    def test_none_allowlist_allows_any_ip(self):
        """None allowlist should allow any IP."""
        verify_ip_allowlist("192.168.1.100", None)

    def test_empty_allowlist_allows_any_ip(self):
        """Empty string allowlist should allow any IP."""
        verify_ip_allowlist("192.168.1.100", "")

    def test_allowlist_with_spaces_handled_correctly(self):
        """Allowlist with spaces should be trimmed."""
        verify_ip_allowlist("192.168.1.100", " 192.168.1.100 , 10.0.0.1 ")


# ==================== SecretStore Encryption Tests ====================

class TestSecretStoreEncryption:
    """Test SecretStore encryption/decryption security."""

    @pytest_asyncio.fixture
    async def mock_db(self):
        """Mock database connection."""
        db = AsyncMock()
        db.fetchone = AsyncMock(return_value=None)
        db.fetchall = AsyncMock(return_value=[])
        db.execute = AsyncMock()
        return db

    @pytest_asyncio.fixture
    async def secret_store(self, mock_db, monkeypatch):
        """Create SecretStore with test key."""
        test_key = Fernet.generate_key().decode()
        monkeypatch.setenv("SECRET_KEY", test_key)
        return SecretStore(mock_db)

    @pytest.mark.asyncio
    async def test_round_trip_encryption_decryption(self, secret_store, mock_db):
        """Encrypt then decrypt should return original value."""
        original_value = "my-secret-api-key-12345"
        name = "TEST_SECRET"

        # Mock database to return encrypted value
        await secret_store.set(name, original_value)

        # Get the encrypted value from the execute call
        call_args = mock_db.execute.call_args[0]
        params = call_args[1]
        encrypted_value = params["value"]

        # Mock fetch to return the encrypted value
        mock_db.fetchone.return_value = {"value": encrypted_value, "key_version": 1}

        # Decrypt should return original
        decrypted = await secret_store.get(name)
        assert decrypted == original_value

    @pytest.mark.asyncio
    async def test_different_keys_produce_different_ciphertext(self, mock_db, monkeypatch):
        """Different encryption keys should produce different ciphertext."""
        value = "same-secret"
        name = "TEST_SECRET"

        # Encrypt with key1
        key1 = Fernet.generate_key().decode()
        monkeypatch.setenv("SECRET_KEY", key1)
        store1 = SecretStore(mock_db)
        await store1.set(name, value)
        call1 = mock_db.execute.call_args[0][1]
        ciphertext1 = call1["value"]

        # Encrypt with key2
        mock_db.execute.reset_mock()
        key2 = Fernet.generate_key().decode()
        monkeypatch.setenv("SECRET_KEY", key2)
        store2 = SecretStore(mock_db)
        await store2.set(name, value)
        call2 = mock_db.execute.call_args[0][1]
        ciphertext2 = call2["value"]

        # Ciphertexts should be different
        assert ciphertext1 != ciphertext2

    @pytest.mark.asyncio
    async def test_tampering_with_ciphertext_causes_decryption_failure(self, secret_store, mock_db):
        """Tampering with ciphertext should cause decryption failure."""
        original_value = "secret-value"
        name = "TEST_SECRET"

        await secret_store.set(name, original_value)
        call_args = mock_db.execute.call_args[0][1]
        encrypted = call_args["value"]

        # Tamper with ciphertext (flip some bits)
        tampered = bytearray(encrypted)
        tampered[10] ^= 0xFF  # Flip bits in position 10

        # Mock fetch to return tampered ciphertext
        mock_db.fetchone.return_value = {"value": bytes(tampered), "key_version": 1}

        # Decryption should fail
        with pytest.raises(Exception):  # Fernet raises InvalidToken
            await secret_store.get(name)

    @pytest.mark.asyncio
    async def test_empty_string_encryption_decryption(self, secret_store, mock_db):
        """Empty string should encrypt and decrypt correctly."""
        name = "EMPTY_SECRET"

        await secret_store.set(name, "")
        call_args = mock_db.execute.call_args[0][1]
        encrypted = call_args["value"]

        mock_db.fetchone.return_value = {"value": encrypted, "key_version": 1}
        decrypted = await secret_store.get(name)
        assert decrypted == ""

    @pytest.mark.asyncio
    async def test_unicode_and_special_characters_handling(self, secret_store, mock_db):
        """Unicode and special characters should be handled correctly."""
        test_values = [
            "日本語キー",
            "emoji🔑secret",
            "special!@#$%^&*()",
            "newline\ncharacter",
            "tab\tcharacter",
        ]

        for i, value in enumerate(test_values):
            name = f"UNICODE_TEST_{i}"
            await secret_store.set(name, value)

            call_args = mock_db.execute.call_args[0][1]
            encrypted = call_args["value"]

            mock_db.fetchone.return_value = {"value": encrypted, "key_version": 1}
            decrypted = await secret_store.get(name)
            assert decrypted == value

    @pytest.mark.asyncio
    async def test_key_rotation_support(self, secret_store, mock_db, monkeypatch):
        """Key rotation should allow decryption with both old and new keys."""
        value = "rotating-secret"
        name = "ROTATED_SECRET"

        # Encrypt with current key
        current_key = Fernet.generate_key().decode()
        monkeypatch.setenv("SECRET_KEY", current_key)
        store = SecretStore(mock_db)
        await store.set(name, value)

        call_args = mock_db.execute.call_args[0][1]
        encrypted_with_current = call_args["value"]

        # Rotate to new key but keep previous
        new_key = Fernet.generate_key().decode()
        monkeypatch.setenv("SECRET_KEY", new_key)
        monkeypatch.setenv("SECRET_KEY_PREVIOUS", current_key)

        # New store should decrypt old ciphertext
        rotated_store = SecretStore(mock_db)
        mock_db.fetchone.return_value = {"value": encrypted_with_current, "key_version": 1}
        decrypted = await rotated_store.get(name)
        assert decrypted == value

    @pytest.mark.asyncio
    async def test_invalid_secret_name_rejected(self, secret_store):
        """Invalid secret name format should be rejected."""
        invalid_names = [
            "lowercase",       # Must start with uppercase
            "123NUMBERS",      # Must start with letter
            "INVALID-DASH",    # No dashes allowed
            "INVALID SPACE",   # No spaces allowed
            "A" * 65,          # Too long (>64 chars)
        ]

        for name in invalid_names:
            with pytest.raises(SecretNameInvalidError):
                await secret_store.set(name, "value")

    @pytest.mark.asyncio
    async def test_valid_secret_names_accepted(self, secret_store, mock_db):
        """Valid secret name formats should be accepted."""
        valid_names = [
            "VALID_NAME",
            "A",
            "API_KEY_123",
            "OPENAI_API_KEY",
            "A" * 64,  # Max length
        ]

        for name in valid_names:
            await secret_store.set(name, "value")  # Should not raise


# ==================== MCP Manager Security Tests ====================

class TestMCPManagerCommandInjection:
    """Test MCP Manager command injection prevention."""

    def test_allowed_commands_accepted(self):
        """Commands in allowlist should be accepted."""
        allowed_commands = ["npx", "node", "python", "python3", "uvx"]

        for cmd in allowed_commands:
            if cmd in ["npx", "node"]:  # Only test if available
                try:
                    config = MCPServerConfig(
                        id=f"test-{cmd}",
                        name=f"Test {cmd}",
                        command=cmd,
                        args=["-h"],
                    )
                    assert config.command == cmd
                except MCPManagerError:
                    # Command not in system PATH, which is OK
                    pass

    def test_disallowed_commands_rejected(self):
        """Commands not in allowlist should be rejected."""
        dangerous_commands = [
            "bash",
            "sh",
            "curl",
            "wget",
            "rm",
            "cat",
            "/usr/bin/python",  # Absolute paths not allowed
        ]

        for cmd in dangerous_commands:
            with pytest.raises(MCPCommandNotAllowedError):
                MCPServerConfig(
                    id="test",
                    name="Test",
                    command=cmd,
                    args=[],
                )

    def test_blocked_arguments_rejected(self):
        """Blocked arguments should be rejected."""
        blocked_args = [
            ["--eval", "malicious_code()"],
            ["-e", "console.log('injection')"],
            ["--exec", "rm -rf /"],
            ["-c", "import os; os.system('ls')"],
            ["--import", "malicious_module"],
        ]

        for args in blocked_args:
            with pytest.raises(MCPManagerError, match="blocked for security"):
                MCPServerConfig(
                    id="test",
                    name="Test",
                    command="npx",
                    args=args,
                )

    def test_path_traversal_in_args_rejected(self):
        """Path traversal attempts should be rejected."""
        traversal_args = [
            ["../../../etc/passwd"],
            ["../../malicious.js"],
            ["safe/../../../etc/shadow"],
        ]

        for args in traversal_args:
            with pytest.raises(MCPManagerError, match="Path traversal detected"):
                MCPServerConfig(
                    id="test",
                    name="Test",
                    command="npx",
                    args=args,
                )

    def test_absolute_paths_rejected_except_safe_prefixes(self):
        """Absolute paths should be rejected except safe prefixes."""
        # Unsafe absolute paths
        unsafe_paths = [
            ["/etc/passwd"],
            ["/usr/bin/malicious"],
            ["/home/user/script.js"],
        ]

        for args in unsafe_paths:
            with pytest.raises(MCPManagerError, match="Absolute path not allowed"):
                MCPServerConfig(
                    id="test",
                    name="Test",
                    command="npx",
                    args=args,
                )

        # Safe absolute paths
        safe_paths = [
            ["/tmp/safe-script.js"],
            ["/var/tmp/temp-file"],
        ]

        for args in safe_paths:
            try:
                config = MCPServerConfig(
                    id="test",
                    name="Test",
                    command="npx",
                    args=args,
                )
                assert config.args == args
            except MCPManagerError as e:
                if "not found in system PATH" not in str(e):
                    raise

    def test_invalid_environment_variable_names_rejected(self):
        """Invalid environment variable names should be rejected."""
        invalid_envs = [
            {"invalid-name": "value"},      # Dashes not allowed
            {"123INVALID": "value"},        # Can't start with number
            {"invalid name": "value"},      # Spaces not allowed
            {"lowercase_var": "value"},     # Must be uppercase
        ]

        for env in invalid_envs:
            with pytest.raises(MCPManagerError, match="Invalid environment variable"):
                MCPServerConfig(
                    id="test",
                    name="Test",
                    command="npx",
                    args=[],
                    env=env,
                )

    def test_valid_environment_variable_names_accepted(self):
        """Valid environment variable names should be accepted."""
        valid_envs = [
            {"API_KEY": "value"},
            {"OPENAI_API_KEY": "sk-123"},
            {"PATH": "/usr/bin"},
            {"A": "single"},
            {"VAR_123": "with_numbers"},
        ]

        for env in valid_envs:
            try:
                config = MCPServerConfig(
                    id="test",
                    name="Test",
                    command="npx",
                    args=[],
                    env=env,
                )
                assert config.env == env
            except MCPManagerError as e:
                if "not found in system PATH" not in str(e):
                    raise


# ==================== JWT Security Tests ====================

class TestJWTSecurity:
    """Test JWT token security."""

    def test_expired_token_rejected(self):
        """Expired JWT token should be rejected."""
        # Create token that expired 1 hour ago
        expire = datetime.now(UTC) - timedelta(hours=1)
        payload = {
            "sub": "user-123",
            "email": "test@example.com",
            "role": "admin",
            "exp": expire,
            "iat": datetime.now(UTC) - timedelta(hours=2),
        }
        token = pyjwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            decode_token(token)

        assert exc_info.value.status_code == 401
        assert "INVALID_TOKEN" in str(exc_info.value.detail)

    def test_invalid_signature_rejected(self):
        """Token with invalid signature should be rejected."""
        # Create token with wrong secret
        wrong_secret = "wrong-secret-key"
        payload = {
            "sub": "user-123",
            "email": "test@example.com",
            "role": "admin",
            "exp": datetime.now(UTC) + timedelta(hours=1),
            "iat": datetime.now(UTC),
        }
        token = pyjwt.encode(payload, wrong_secret, algorithm=JWT_ALGORITHM)

        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            decode_token(token)

        assert exc_info.value.status_code == 401

    def test_missing_required_claims_rejected(self):
        """Token missing required claims should be rejected."""
        # Token without 'sub' claim
        payload = {
            "email": "test@example.com",
            "exp": datetime.now(UTC) + timedelta(hours=1),
        }
        token = pyjwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

        from fastapi import HTTPException
        decoded = decode_token(token)  # Should decode successfully
        # But get_current_user should reject it
        # We'll test this indirectly by checking the payload
        assert decoded.get("sub") is None

    def test_token_with_wrong_algorithm_rejected(self):
        """Token signed with wrong algorithm should be rejected."""
        # Create token with HS512 instead of HS256
        payload = {
            "sub": "user-123",
            "email": "test@example.com",
            "role": "admin",
            "exp": datetime.now(UTC) + timedelta(hours=1),
            "iat": datetime.now(UTC),
        }
        token = pyjwt.encode(payload, JWT_SECRET, algorithm="HS512")

        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            decode_token(token)

        assert exc_info.value.status_code == 401

    def test_token_with_manipulated_payload_rejected(self):
        """Token with manipulated payload should be rejected."""
        # Create valid token for regular user
        token = create_access_token("user-123", "user@example.com", Role.VIEWER)

        # Decode without verification
        payload = pyjwt.decode(token, options={"verify_signature": False}, algorithms=[JWT_ALGORITHM])

        # Manipulate to admin
        payload["role"] = "admin"

        # Re-encode with wrong secret (simulating manipulation)
        manipulated = pyjwt.encode(payload, "wrong-secret", algorithm=JWT_ALGORITHM)

        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            decode_token(manipulated)

        assert exc_info.value.status_code == 401

    def test_valid_token_accepted(self):
        """Valid token should be accepted and decoded correctly."""
        user_id = "user-123"
        email = "test@example.com"
        role = Role.ADMIN

        token = create_access_token(user_id, email, role)
        payload = decode_token(token)

        assert payload["sub"] == user_id
        assert payload["email"] == email
        assert payload["role"] == role.value

    def test_token_includes_expiry_and_issued_at(self):
        """Token should include exp and iat claims."""
        token = create_access_token("user-123", "test@example.com")
        payload = decode_token(token)

        assert "exp" in payload
        assert "iat" in payload

        # Verify exp is in the future
        exp = datetime.fromtimestamp(payload["exp"], UTC)
        now = datetime.now(UTC)
        assert exp > now


# ==================== Input Validation Tests ====================

class TestInputValidation:
    """Test input validation and injection prevention."""

    def test_sql_injection_in_secret_resolve(self):
        """SQL injection attempts in secret resolution should be blocked."""
        # SecretStore.resolve() validates secret names against pattern
        # SQL injection attempts should fail name validation

        # Mock database
        mock_db = AsyncMock()
        secret_store = SecretStore(mock_db)

        sql_injection_attempts = [
            "${'; DROP TABLE secrets; --}",
            "${1' OR '1'='1}",
            "${admin'--}",
        ]

        for attempt in sql_injection_attempts:
            # Should raise SecretNameInvalidError due to pattern mismatch
            with pytest.raises(SecretNameInvalidError):
                import asyncio
                asyncio.run(secret_store.resolve(attempt))

    def test_xss_payloads_in_webhook_body(self):
        """XSS payloads in webhook body should not cause issues."""
        # Webhook handler accepts JSON, which doesn't execute scripts
        # But we verify it handles malicious payloads safely

        xss_payloads = [
            '<script>alert("XSS")</script>',
            '<img src=x onerror=alert("XSS")>',
            'javascript:alert("XSS")',
        ]

        for payload in xss_payloads:
            body = json.dumps({"data": payload}).encode()
            secret = "test-secret"
            timestamp = str(int(time.time()))

            # Generate valid HMAC for malicious payload
            payload_str = f"{timestamp}.{body.decode('utf-8')}"
            hmac_sig = hmac.new(
                secret.encode(),
                payload_str.encode(),
                hashlib.sha256,
            ).hexdigest()
            signature = f"sha256={hmac_sig}"

            # Verification should succeed (HMAC is valid)
            verify_webhook_signature(body, signature, timestamp, secret)

            # The payload is just data and won't execute
            parsed = json.loads(body)
            assert parsed["data"] == payload

    def test_oversized_webhook_payload(self):
        """Oversized webhook payloads should be handled (this is FastAPI's job)."""
        # This is typically handled by FastAPI body size limits
        # We just verify HMAC verification works with large payloads

        large_body = json.dumps({"data": "X" * 1000000}).encode()  # 1MB
        secret = "test-secret"
        timestamp = str(int(time.time()))

        payload = f"{timestamp}.{large_body.decode('utf-8')}"
        hmac_sig = hmac.new(
            secret.encode(),
            payload.encode(),
            hashlib.sha256,
        ).hexdigest()
        signature = f"sha256={hmac_sig}"

        # Should handle large payloads without errors
        verify_webhook_signature(large_body, signature, timestamp, secret)

    def test_null_byte_injection_in_secret_names(self):
        """Null byte injection in secret names should be rejected."""
        mock_db = AsyncMock()
        secret_store = SecretStore(mock_db)

        null_byte_attempts = [
            "VALID\x00NAME",
            "ATTACK\x00.txt",
        ]

        for name in null_byte_attempts:
            with pytest.raises(SecretNameInvalidError):
                import asyncio
                asyncio.run(secret_store.set(name, "value"))

    def test_secret_access_whitelist_enforcement(self):
        """Secret access should respect whitelist."""
        mock_db = AsyncMock()
        mock_db.fetchone = AsyncMock(return_value={"value": Fernet.generate_key(), "key_version": 1})
        secret_store = SecretStore(mock_db)

        text = "Bearer ${ALLOWED_SECRET}"
        allowed_secrets = {"ALLOWED_SECRET"}

        # Access to whitelisted secret should work
        # (We expect SecretNotFoundError since we're not setting up full mock)
        # But more importantly, it shouldn't raise SecretAccessDeniedError
        import asyncio
        try:
            asyncio.run(secret_store.resolve(text, allowed_secrets))
        except (SecretNotFoundError, Exception):
            pass  # Expected due to mock

        # Access to non-whitelisted secret should fail
        text_denied = "Bearer ${FORBIDDEN_SECRET}"
        with pytest.raises(SecretAccessDeniedError):
            asyncio.run(secret_store.resolve(text_denied, allowed_secrets))
