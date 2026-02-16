"""Tests for auth input validation."""
import pytest
from app.api.auth import RegisterRequest, LoginRequest
from pydantic import ValidationError


class TestRegisterValidation:
    def test_valid_registration(self):
        req = RegisterRequest(email="test@example.com", password="securepass123")
        assert req.email == "test@example.com"
        assert req.password == "securepass123"

    def test_empty_password_rejected(self):
        with pytest.raises(ValidationError):
            RegisterRequest(email="test@example.com", password="")

    def test_short_password_rejected(self):
        with pytest.raises(ValidationError):
            RegisterRequest(email="test@example.com", password="short")

    def test_too_long_password_rejected(self):
        with pytest.raises(ValidationError):
            RegisterRequest(email="test@example.com", password="a" * 129)

    def test_invalid_email_rejected(self):
        with pytest.raises(ValidationError):
            RegisterRequest(email="not-an-email", password="securepass123")

    def test_empty_email_rejected(self):
        with pytest.raises(ValidationError):
            RegisterRequest(email="", password="securepass123")


class TestLoginValidation:
    def test_valid_login(self):
        req = LoginRequest(email="test@example.com", password="anypassword")
        assert req.email == "test@example.com"

    def test_invalid_email_rejected(self):
        with pytest.raises(ValidationError):
            LoginRequest(email="bad-email", password="password123")

    def test_empty_password_rejected(self):
        with pytest.raises(ValidationError):
            LoginRequest(email="test@example.com", password="")
