"""Verifies Clerk-issued session JWTs via Clerk's published JWKS — no Clerk
SDK/network call needed beyond fetching (and caching) that public key set.

Setup once you have a Clerk instance: set CLERK_JWKS_URL to
`https://<your-clerk-frontend-api>/.well-known/jwks.json` (shown on the
Clerk dashboard's API Keys page) and CLERK_ISSUER to that same frontend API
origin. This assumes Clerk's default session claims (`sub` = user id,
`org_id`/`org_role` = the active organization) — enable the Organizations
feature in the Clerk dashboard and confirm these claim names against your
instance's "Session token" preview before going live; Clerk has changed this
shape across versions.
"""
import os
from typing import Any, Dict, Optional

import jwt
from jwt import PyJWKClient

CLERK_JWKS_URL = os.environ.get("CLERK_JWKS_URL", "")
CLERK_ISSUER = os.environ.get("CLERK_ISSUER", "")

# Clerk's default session token does NOT include email — add a custom claim
# in the Clerk dashboard (Sessions -> Customize session token):
#   {"email": "{{user.primary_email_address}}"}
# or provisioning falls back to a placeholder derived from the user id.

_jwk_client: Optional[PyJWKClient] = None


class NoActiveOrganization(Exception):
    """Raised when a Clerk session has no active organization selected.
    CloudWise requires org context on every request (see db/init.sql RLS).
    """


def _get_jwk_client() -> PyJWKClient:
    global _jwk_client
    if _jwk_client is None:
        if not CLERK_JWKS_URL:
            raise RuntimeError("CLERK_JWKS_URL is not configured")
        _jwk_client = PyJWKClient(CLERK_JWKS_URL)
    return _jwk_client


def verify_clerk_token(token: str) -> Dict[str, Any]:
    client = _get_jwk_client()
    signing_key = client.get_signing_key_from_jwt(token)
    return jwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256"],
        issuer=CLERK_ISSUER or None,
        options={"verify_aud": False},
    )


def extract_identity(payload: Dict[str, Any]) -> Dict[str, Any]:
    clerk_user_id = payload["sub"]
    clerk_org_id = payload.get("org_id")
    if not clerk_org_id:
        raise NoActiveOrganization(
            "Clerk session has no active organization; the frontend must "
            "have the user select or create one before calling the API."
        )
    return {
        "clerk_user_id": clerk_user_id,
        "clerk_org_id": clerk_org_id,
        "org_role": payload.get("org_role"),
        "org_name": payload.get("org_slug") or clerk_org_id,
        "email": payload.get("email") or f"{clerk_user_id}@users.clerk.invalid",
    }
