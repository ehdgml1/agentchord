"""PII filtering for logs and audit."""
import re
from typing import Any

PII_PATTERNS = [
    (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]'),
    (r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', '[PHONE]'),
    (r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b', '[CARD]'),
    (r'\b\d{3}-\d{2}-\d{4}\b', '[SSN]'),
    (r'password["\']?\s*[:=]\s*["\']?[^"\'\s]+', 'password=[REDACTED]'),
    (r'api[_-]?key["\']?\s*[:=]\s*["\']?[^"\'\s]+', 'api_key=[REDACTED]'),
    (r'secret["\']?\s*[:=]\s*["\']?[^"\'\s]+', 'secret=[REDACTED]'),
]


def sanitize_pii(data: Any) -> Any:
    """Remove PII from data.

    Args:
        data: Data to sanitize (str, dict, list, or other).

    Returns:
        Sanitized copy of data with PII redacted.
    """
    if isinstance(data, str):
        return _sanitize_string(data)
    elif isinstance(data, dict):
        return {k: sanitize_pii(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [sanitize_pii(item) for item in data]
    return data


def _sanitize_string(text: str) -> str:
    """Sanitize PII from string.

    Args:
        text: String to sanitize.

    Returns:
        Sanitized string.
    """
    for pattern, replacement in PII_PATTERNS:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text
