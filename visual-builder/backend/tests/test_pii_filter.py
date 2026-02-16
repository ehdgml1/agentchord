"""Tests for PII filtering."""
import pytest
from app.core.pii_filter import sanitize_pii


class TestSanitizePII:
    """Tests for sanitize_pii function."""

    def test_email_redaction(self):
        """Emails should be redacted."""
        text = "contact: test@example.com"
        result = sanitize_pii(text)
        assert "[EMAIL]" in result
        assert "test@example.com" not in result

    def test_multiple_emails_redaction(self):
        """Multiple emails should be redacted."""
        text = "Send to john@example.com and jane@test.org"
        result = sanitize_pii(text)
        assert result.count("[EMAIL]") == 2
        assert "john@example.com" not in result
        assert "jane@test.org" not in result

    def test_phone_redaction(self):
        """Phone numbers should be redacted."""
        text = "call 123-456-7890"
        result = sanitize_pii(text)
        assert "[PHONE]" in result
        assert "123-456-7890" not in result

    def test_phone_various_formats(self):
        """Phone numbers in various formats should be redacted."""
        test_cases = [
            "123-456-7890",
            "123.456.7890",
            "1234567890",
        ]
        for phone in test_cases:
            result = sanitize_pii(f"call {phone}")
            assert "[PHONE]" in result
            assert phone not in result

    def test_card_redaction(self):
        """Credit card numbers should be redacted."""
        text = "card: 1234-5678-9012-3456"
        result = sanitize_pii(text)
        assert "[CARD]" in result
        assert "1234-5678-9012-3456" not in result

    def test_card_various_formats(self):
        """Credit cards in various formats should be redacted."""
        test_cases = [
            "1234-5678-9012-3456",
            "1234 5678 9012 3456",
            "1234567890123456",
        ]
        for card in test_cases:
            result = sanitize_pii(f"card: {card}")
            assert "[CARD]" in result
            assert card not in result

    def test_ssn_redaction(self):
        """SSN should be redacted."""
        text = "SSN: 123-45-6789"
        result = sanitize_pii(text)
        assert "[SSN]" in result
        assert "123-45-6789" not in result

    def test_password_redaction(self):
        """Passwords should be redacted."""
        test_cases = [
            'password="secret123"',
            "password: secret123",
            "password=secret123",
            "password='secret123'",
        ]
        for text in test_cases:
            result = sanitize_pii(text)
            assert "[REDACTED]" in result
            assert "secret123" not in result

    def test_api_key_redaction(self):
        """API keys should be redacted."""
        test_cases = [
            'api_key="sk-1234567890"',
            "api-key: sk-1234567890",
            "apikey=sk-1234567890",
        ]
        for text in test_cases:
            result = sanitize_pii(text)
            assert "[REDACTED]" in result
            assert "sk-1234567890" not in result

    def test_secret_redaction(self):
        """Secrets should be redacted."""
        text = 'secret="my-secret-value"'
        result = sanitize_pii(text)
        assert "[REDACTED]" in result
        assert "my-secret-value" not in result

    def test_nested_dict_sanitization(self):
        """Nested dictionaries should be sanitized recursively."""
        data = {
            "user": {
                "email": "test@example.com",
                "name": "John",
                "phone": "123-456-7890",
            },
            "metadata": {
                "ip": "192.168.1.1",
            },
        }
        result = sanitize_pii(data)
        assert "[EMAIL]" in result["user"]["email"]
        assert result["user"]["name"] == "John"
        assert "[PHONE]" in result["user"]["phone"]
        assert result["metadata"]["ip"] == "192.168.1.1"

    def test_list_sanitization(self):
        """Lists should be sanitized recursively."""
        data = [
            "Email: test@example.com",
            "Phone: 123-456-7890",
            "Name: John",
        ]
        result = sanitize_pii(data)
        assert "[EMAIL]" in result[0]
        assert "[PHONE]" in result[1]
        assert result[2] == "Name: John"

    def test_mixed_nested_structure(self):
        """Complex nested structures should be sanitized."""
        data = {
            "users": [
                {"email": "user1@test.com", "creds": 'password="pass123"'},
                {"email": "user2@test.com", "key": 'api_key="sk-abc"'},
            ],
            "contact": "support@example.com",
        }
        result = sanitize_pii(data)
        assert "[EMAIL]" in result["users"][0]["email"]
        assert "[REDACTED]" in result["users"][0]["creds"]
        assert "[EMAIL]" in result["users"][1]["email"]
        assert "[REDACTED]" in result["users"][1]["key"]
        assert "[EMAIL]" in result["contact"]

    def test_non_string_types_unchanged(self):
        """Non-string types should pass through unchanged."""
        assert sanitize_pii(123) == 123
        assert sanitize_pii(45.67) == 45.67
        assert sanitize_pii(True) is True
        assert sanitize_pii(None) is None

    def test_empty_string(self):
        """Empty strings should be handled."""
        assert sanitize_pii("") == ""

    def test_no_pii_unchanged(self):
        """Text without PII should be unchanged."""
        text = "This is a regular message with no sensitive data"
        result = sanitize_pii(text)
        assert result == text

    def test_partial_matches_not_redacted(self):
        """Partial matches that aren't valid PII shouldn't be redacted."""
        text = "The number 123 and text@domain is incomplete"
        result = sanitize_pii(text)
        # Should still find complete patterns if present
        assert "123" in result  # Not a complete phone number
