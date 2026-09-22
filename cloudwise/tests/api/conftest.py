import os
import pathlib
import subprocess
import sys
import uuid

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

ROOT = pathlib.Path(__file__).resolve().parents[2]  # cloudwise/
API_DIR = ROOT / "apps" / "api"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(API_DIR))

TEST_DB_NAME = "cloudwise_test"
# Must be the unprivileged cloudwise_app role (created by init.sql), never the
# superuser running schema setup below — see db/init.sql for why that matters.
os.environ.setdefault(
    "DATABASE_URL",
    f"postgresql+psycopg://cloudwise_app:cloudwise_app_dev_password@localhost/{TEST_DB_NAME}",
)
os.environ.setdefault("CLERK_ISSUER", "https://test.clerk.accounts.dev")

INIT_SQL = API_DIR / "db" / "init.sql"

TABLES = "organizations, users, aws_accounts, findings, change_requests, audit_log"

# Schema setup/teardown runs as an admin/superuser (never cloudwise_app — see
# db/init.sql for why). Locally that's just the current OS user via a
# Homebrew/local Postgres's default trust auth; CI sets TEST_PG* to the
# postgres service container's superuser instead.
_PSQL_ENV = dict(os.environ)
_PSQL_ENV["PGHOST"] = os.environ.get("TEST_PGHOST", "localhost")
if "TEST_PGUSER" in os.environ:
    _PSQL_ENV["PGUSER"] = os.environ["TEST_PGUSER"]
if "TEST_PGPASSWORD" in os.environ:
    _PSQL_ENV["PGPASSWORD"] = os.environ["TEST_PGPASSWORD"]


def _psql(*args: str) -> None:
    subprocess.run(
        ["psql", "-d", TEST_DB_NAME, "-v", "ON_ERROR_STOP=1", *args],
        check=True,
        capture_output=True,
        text=True,
        env=_PSQL_ENV,
    )


@pytest.fixture(scope="session", autouse=True)
def _reset_schema_once():
    _psql("-c", "DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
    _psql("-f", str(INIT_SQL))
    yield


@pytest.fixture(autouse=True)
def _truncate_between_tests():
    yield
    _psql("-c", f"TRUNCATE {TABLES} CASCADE;")


_RSA_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_PRIVATE_PEM = _RSA_KEY.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption(),
)
_PUBLIC_KEY = _RSA_KEY.public_key()


class _FakeSigningKey:
    def __init__(self, key):
        self.key = key


class _FakeJWKClient:
    def get_signing_key_from_jwt(self, token):
        return _FakeSigningKey(_PUBLIC_KEY)


@pytest.fixture(autouse=True)
def _patch_clerk_jwks(monkeypatch):
    from app import clerk_auth

    monkeypatch.setattr(clerk_auth, "_jwk_client", _FakeJWKClient())


def _make_clerk_token(
    clerk_user_id: str = None,
    clerk_org_id: str = None,
    email: str = None,
    org_role: str = "org:admin",
    org_slug: str = "acme-inc",
    issuer: str = None,
) -> str:
    clerk_user_id = clerk_user_id or f"user_{uuid.uuid4().hex[:16]}"
    clerk_org_id = clerk_org_id or f"org_{uuid.uuid4().hex[:16]}"
    email = email or f"{clerk_user_id}@acmecorp.io"
    payload = {
        "sub": clerk_user_id,
        "org_id": clerk_org_id,
        "org_role": org_role,
        "org_slug": org_slug,
        "email": email,
        "iss": issuer or os.environ["CLERK_ISSUER"],
    }
    return jwt.encode(payload, _PRIVATE_PEM, algorithm="RS256")


@pytest.fixture
def make_clerk_token():
    return _make_clerk_token


@pytest.fixture
def sign_raw_claims():
    """For tests that need a token with unusual/missing claims (e.g. no
    org_id at all), rather than the well-formed shape make_clerk_token gives.
    """

    def _sign(payload: dict) -> str:
        return jwt.encode(payload, _PRIVATE_PEM, algorithm="RS256")

    return _sign


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    from app.main import app

    return TestClient(app)
