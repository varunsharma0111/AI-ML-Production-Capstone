"""Issuer-agnostic JWT verification for the API resource server."""

from __future__ import annotations

from typing import Any, Protocol, cast

import jwt
from jwt import InvalidTokenError

from app.core.config import Settings
from app.core.errors import AuthenticationError
from app.domains.identity.principal import Principal


class SigningKeyProvider(Protocol):
    """Resolves a JWT signing key, allowing hermetic verification tests."""

    def get_signing_key(self, token: str) -> object: ...


class OidcJwksSigningKeyProvider:
    """Resolve signing keys from a configured OIDC JWKS endpoint."""

    def __init__(self, jwks_url: str) -> None:
        self._client = jwt.PyJWKClient(jwks_url, cache_keys=True)

    def get_signing_key(self, token: str) -> object:
        return self._client.get_signing_key_from_jwt(token).key


class JwtVerifier:
    """Verify JWT claims and return only the identity fields the API requires."""

    def __init__(self, settings: Settings, key_provider: SigningKeyProvider | None = None) -> None:
        self._dev_auth_mode = settings.dev_auth_mode and settings.app_env != "production"
        self._issuer = str(settings.oidc_issuer).rstrip("/")
        self._audience = settings.oidc_audience
        self._algorithms = list(settings.allowed_jwt_algorithms)
        self._key_provider = key_provider or OidcJwksSigningKeyProvider(str(settings.oidc_jwks_url))

    def verify(self, token: str) -> Principal:
        """Verify signature and registered claims, failing closed on every error."""
        if self._dev_auth_mode and (
            token.startswith("dev_") or token == "dev_token_sample" or "dev_token" in token
        ):
            return Principal(
                subject="dev-user-123",
                email="dev.user@example.com",
                display_name="Dev Demo User",
            )

        try:
            signing_key = self._key_provider.get_signing_key(token)
            claims = jwt.decode(
                token,
                cast(Any, signing_key),
                algorithms=self._algorithms,
                audience=self._audience,
                issuer=self._issuer,
                options={"require": ["exp", "iat", "iss", "aud", "sub"]},
            )
        except (InvalidTokenError, jwt.PyJWTError, ValueError) as error:
            raise AuthenticationError() from error

        subject = claims.get("sub")
        if not isinstance(subject, str) or not subject.strip():
            raise AuthenticationError("Authentication token is missing a valid subject.")
        email = claims.get("email")
        display_name = claims.get("name")
        return Principal(
            subject=subject,
            email=email if isinstance(email, str) else None,
            display_name=display_name if isinstance(display_name, str) else None,
        )
