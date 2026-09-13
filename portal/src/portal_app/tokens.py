"""Signing keys, short-lived app tokens (JWT), and HMAC-sealed state/session blobs.

The portal's private key is the single trust anchor: connected apps only ever
see the public half, published at /.well-known/jwks.json. A name in a request
body is a claim, never an identity — only a valid signature counts.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from pathlib import Path

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


def generate_keypair(path: Path) -> None:
    """Write a fresh Ed25519 private key PEM with owner-only permissions."""
    private = Ed25519PrivateKey.generate()
    pem = private.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(pem)
    path.chmod(0o600)


class Signer:
    """Signs app tokens; publishes only the public key as JWKS."""

    def __init__(self, key_path: str) -> None:
        self._private = serialization.load_pem_private_key(
            Path(key_path).read_bytes(), password=None
        )
        if not isinstance(self._private, Ed25519PrivateKey):
            raise TypeError("portal key must be Ed25519; regenerate with portal_app.keygen")
        public_der = self._private.public_key().public_bytes(
            serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
        )
        self.kid = hashlib.sha256(public_der).hexdigest()[:16]

    def sign(self, claims: dict) -> str:
        return jwt.encode(claims, self._private, algorithm="EdDSA", headers={"kid": self.kid})

    def jwk(self) -> dict:
        jwk = json.loads(jwt.algorithms.OKPAlgorithm.to_jwk(self._private.public_key()))
        return jwk | {"kid": self.kid, "use": "sig", "alg": "EdDSA"}


def seal(payload: dict, secret: str, ttl: int) -> str:
    """HMAC-seal a small payload (login state, session) into one opaque string."""
    body = base64.urlsafe_b64encode(
        json.dumps({**payload, "exp": int(time.time()) + ttl}, separators=(",", ":")).encode()
    ).decode()
    signature = hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()
    return f"{body}.{signature}"


def unseal(token: str, secret: str) -> dict | None:
    """Reverse seal(); None for any tampering, malformation, or expiry."""
    try:
        body, signature = token.split(".")
    except ValueError:
        return None
    expected = hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        return None
    try:
        payload = json.loads(base64.urlsafe_b64decode(body.encode()))
    except (ValueError, UnicodeDecodeError):
        return None
    if not isinstance(payload, dict) or payload.get("exp", 0) < time.time():
        return None
    return payload
