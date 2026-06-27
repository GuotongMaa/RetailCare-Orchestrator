"""Demo authentication: resolve the trusted customer identity from a bearer token.

The API — not the request body, and never the model — is the trust boundary for
`user_id` (docs/state-and-security-upgrade.md D11). For the demo we map opaque bearer
tokens to user ids; the default scheme is `Bearer demo-<user_id>`. Swap `resolve_token`
for an OIDC/JWT verifier in production without touching the endpoints.
"""
from __future__ import annotations

import os

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


def resolve_token(token: str) -> str | None:
    """Map a bearer token to a user id, or None if it is not recognised."""
    token = (token or "").strip()
    if not token:
        return None
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
