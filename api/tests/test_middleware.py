"""Cognito JWT middleware tests — sign real RS256 tokens with a throwaway RSA
keypair and patch the JWKS fetch, so signature/expiry/issuer checks run for real
without any network call."""
import os
import time

# Env must be set before importing auth (ISSUER is computed at import).
os.environ.setdefault("COGNITO_REGION", "us-east-1")
os.environ.setdefault("COGNITO_USER_POOL_ID", "us-east-1_TESTPOOL")
os.environ.setdefault("COGNITO_CLIENT_ID", "test-client-id")

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from jose import jwt
from jose import jwk as jose_jwk

from src.middleware import auth

_KID = "test-kid"


@pytest.fixture(scope="module")
def keypair():
    """Return (private_pem_str, jwks_dict) for a fresh RSA-2048 key."""
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    public_pem = key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()

    jwk_dict = jose_jwk.construct(public_pem, "RS256").to_dict()
    # jose may return n/e as bytes — coerce to str so it round-trips like real JWKS.
    jwk_dict = {k: (v.decode() if isinstance(v, bytes) else v) for k, v in jwk_dict.items()}
    jwk_dict["kid"] = _KID
    return private_pem, {"keys": [jwk_dict]}


def _make_token(private_pem: str, exp_offset: int = 3600, token_use: str = "access") -> str:
    now = int(time.time())
    claims = {
        "sub": "user-123",
        "iss": auth.ISSUER,
        "token_use": token_use,
        "iat": now,
        "exp": now + exp_offset,
    }
    return jwt.encode(claims, private_pem, algorithm="RS256", headers={"kid": _KID})


def _event(token: str | None) -> dict:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    return {"headers": headers}


def test_valid_jwt_passes(keypair, monkeypatch):
    private_pem, jwks = keypair
    monkeypatch.setattr(auth, "_fetch_jwks", lambda: jwks)
    claims = auth.get_claims(_event(_make_token(private_pem)))
    assert claims["sub"] == "user-123"
    assert claims["token_use"] == "access"


def test_expired_jwt_401(keypair, monkeypatch):
    private_pem, jwks = keypair
    monkeypatch.setattr(auth, "_fetch_jwks", lambda: jwks)
    with pytest.raises(auth.Unauthorized):
        auth.get_claims(_event(_make_token(private_pem, exp_offset=-30)))


def test_missing_jwt_401():
    with pytest.raises(auth.Unauthorized):
        auth.get_claims(_event(None))
