import os
import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]  # cloudwise/
API_DIR = ROOT / "apps" / "api"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(API_DIR))

TEST_DB_NAME = "cloudwise_test"
os.environ.setdefault(
    "DATABASE_URL",
    f"postgresql+psycopg://cloudwise_app:cloudwise_app_dev_password@localhost/{TEST_DB_NAME}",
)
os.environ.setdefault("CLERK_ISSUER", "https://test.clerk.accounts.dev")

INIT_SQL = API_DIR / "db" / "init.sql"
TABLES = "organizations, users, aws_accounts, findings, change_requests, audit_log, spend_daily"

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
