"""Cognito JWT validation.

API Gateway already enforces a Cognito User Pool authorizer at the edge, but the
handler validates the token again here (defense in depth) so the auth contract is
unit-testable without deploying — and so a misconfigured gateway can never let an
unauthenticated request reach business logic.

Validation steps (RS256):
  1. Pull the bearer token from the Authorization header.
  2. Read the unverified `kid`, find the matching public key in the pool's JWKS.
  3. jose.jwt.decode verifies signature + expiry + issuer.
  4. token_use must be "id" or "access".

`_fetch_jwks` is the single network call and is patched in unit tests.
"""
import json
import os
import urllib.request

from jose import jwt
from jose.exceptions import JWTError


class Unauthorized(Exception):
    """Raised when a request carries no valid Cognito JWT."""


COGNITO_REGION = (
    os.environ.get("COGNITO_REGION")
    or os.environ.get("AWS_REGION")
    or os.environ.get("AWS_DEFAULT_REGION")
    or "us-east-1"
)
USER_POOL_ID = os.environ.get("COGNITO_USER_POOL_ID", "")
APP_CLIENT_ID = os.environ.get("COGNITO_CLIENT_ID", "")

ISSUER = f"https://cognito-idp.{COGNITO_REGION}.amazonaws.com/{USER_POOL_ID}"
JWKS_URL = f"{ISSUER}/.well-known/jwks.json"

_JWKS_CACHE: dict = {}


def _fetch_jwks() -> dict:
    """Fetch and cache the User Pool's JWKS. Patched in unit tests."""
    if not _JWKS_CACHE:
        with urllib.request.urlopen(JWKS_URL, timeout=5) as resp:  # nosec B310
            _JWKS_CACHE.update(json.loads(resp.read()))
    return _JWKS_CACHE


def _extract_bearer(event: dict) -> str | None:
    headers = event.get("headers") or {}
    for key, value in headers.items():
        if key.lower() == "authorization" and value:
            parts = value.split()
            if len(parts) == 2 and parts[0].lower() == "bearer":
                return parts[1]
            return value  # tolerate a bare token
    return None


def get_claims(event: dict) -> dict:
    """Return the validated JWT claims, or raise Unauthorized."""
    token = _extract_bearer(event)
    if not token:
        raise Unauthorized("Missing Authorization bearer token")

    try:
        kid = jwt.get_unverified_header(token).get("kid")
    except JWTError as exc:
        raise Unauthorized(f"Malformed token: {exc}") from exc

    key = next((k for k in _fetch_jwks().get("keys", []) if k.get("kid") == kid), None)
    if key is None:
        raise Unauthorized("No matching signing key for token kid")

    try:
        claims = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            issuer=ISSUER,
            options={"verify_aud": False},  # Cognito access tokens carry no aud claim
        )
    except JWTError as exc:  # expired, wrong issuer, bad signature
        raise Unauthorized(str(exc)) from exc

    if claims.get("token_use") not in ("id", "access"):
        raise Unauthorized("Unexpected token_use")
    return claims
