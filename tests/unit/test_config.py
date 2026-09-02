"""Unit tests for environment configuration and settings parsing."""

import pytest

from app.core.config import Settings


def test_settings_allowed_jwt_algorithms_string_parsing() -> None:
    """Verify ALLOWED_JWT_ALGORITHMS parses raw strings and comma-separated values cleanly."""
    s1 = Settings(allowed_jwt_algorithms="RS256")
    assert s1.allowed_jwt_algorithms == ("RS256",)

    s2 = Settings(allowed_jwt_algorithms="RS256, ES256")
    assert s2.allowed_jwt_algorithms == ("RS256", "ES256")

    s3 = Settings(allowed_jwt_algorithms='["RS256", "RS384"]')
    assert s3.allowed_jwt_algorithms == ("RS256", "RS384")

    s4 = Settings(allowed_jwt_algorithms=("RS256",))
    assert s4.allowed_jwt_algorithms == ("RS256",)


def test_settings_allowed_jwt_algorithms_invalid() -> None:
    """Verify invalid algorithms raise ValueError during validation."""
    msg = "ALLOWED_JWT_ALGORITHMS must contain supported asymmetric algorithms"
    with pytest.raises(ValueError, match=msg):
        Settings(allowed_jwt_algorithms="INVALID_ALG")

