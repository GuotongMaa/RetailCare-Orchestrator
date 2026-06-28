"""Authentication: resolve the trusted customer identity from a bearer token.

The API — not the request body, and never the model — is the trust boundary for
`user_id` (the upgrade design notes D11/C6).

Two modes, chosen by environment:
- **Production**: if `RETAILCARE_JWT_SECRET` is set, bearer tokens are verified as
  HS256 JWTs (signature + `exp`); the customer id is the `sub` claim. (Stdlib only;
  swap `_verify_jwt` for an RS256/JWKS/OIDC verifier without touching the endpoints.)
- **Demo**: otherwise, opaque tokens map to user ids — explicit map via
  `RETAILCARE_DEMO_TOKENS="tokA:u1,..."` or the `Bearer demo-<user_id>` scheme.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time

from fastapi import Header, HTTPException

_DEMO_PREFIX = "demo-"


def _demo_token_map() -> dict[str, str]:
    """Optional explicit map via env: RETAILCARE_DEMO_TOKENS="tokA:u1,tokB:u2"."""
    raw = os.getenv("RETAILCARE_DEMO_TOKENS", "").strip()
    out: dict[str, str] = {}
    for pair in raw.split(","):
        if ":" in pair:
            tok, uid = pair.split(":", 1)
            out[tok.strip()] = uid.strip()
    return out


def _b64url_decode(seg: str) -> bytes:
    return base64.urlsafe_b64decode(seg + "=" * (-len(seg) % 4))


def _verify_jwt(token: str, secret: str) -> str | None:
    """Verify an HS256 JWT and return its `sub`, or None. Rejects alg confusion
    (e.g. 'none') and expired tokens. Constant-time signature comparison."""
    parts = token.split(".")
    if len(parts) != 3:
        return None
    header_b64, payload_b64, sig_b64 = parts
    try:
        header = json.loads(_b64url_decode(header_b64))
        if header.get("alg") != "HS256":
            return None
        expected = hmac.new(secret.encode(), f"{header_b64}.{payload_b64}".encode(),
                            hashlib.sha256).digest()
        if not hmac.compare_digest(expected, _b64url_decode(sig_b64)):
            return None
        payload = json.loads(_b64url_decode(payload_b64))
    except (ValueError, KeyError, json.JSONDecodeError):
        return None
    exp = payload.get("exp")
    if exp is not None and time.time() > float(exp):
        return None
    sub = payload.get("sub")
    return sub if isinstance(sub, str) and sub else None


def resolve_token(token: str) -> str | None:
    """Map a bearer token to a user id, or None if it is not recognised/valid."""
    token = (token or "").strip()
    if not token:
        return None
    secret = os.getenv("RETAILCARE_JWT_SECRET")
    if secret:  # production: JWT only, demo scheme disabled
        return _verify_jwt(token, secret)
    explicit = _demo_token_map()
    if token in explicit:
        return explicit[token]
    if token.startswith(_DEMO_PREFIX) and len(token) > len(_DEMO_PREFIX):
        return token[len(_DEMO_PREFIX):]
    return None


def current_user(authorization: str | None = Header(default=None)) -> str:
    """FastAPI dependency: the authenticated customer, or 401. Fail-closed."""
    parts = (authorization or "").split(None, 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="missing or malformed bearer token")
    uid = resolve_token(parts[1])
    if not uid:
        raise HTTPException(status_code=401, detail="invalid token")
    return uid
