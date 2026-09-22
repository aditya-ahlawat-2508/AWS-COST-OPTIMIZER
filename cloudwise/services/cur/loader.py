"""Writes parsed CUR spend records into Postgres. This is the one place
services/ code reaches into apps/api's models — by design, per the
blueprint's architecture: the CUR ingester and the API share the same
Postgres ("warehouse" at this stage of scale, see docs/blueprint.md).
Running this outside of the test suite needs both `services/` and
`apps/api/` on PYTHONPATH.
"""
import csv
from pathlib import Path
from typing import Dict, Iterable, List, Union
from uuid import UUID

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy import select
from sqlalchemy.orm import Session

from .parser import DailyServiceSpend


def read_cur_csv(path: Union[str, Path]) -> List[Dict]:
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def upsert_spend_daily(session: Session, org_id: UUID, spend_records: Iterable[DailyServiceSpend]) -> int:
    """Must be called on a session already scoped to org_id (see
    app.database.org_scoped_session) so RLS lets these writes through and the
    account lookup below only sees this org's own connected accounts.
    Returns the number of records written (records for AWS accounts not yet
    connected to CloudWise are skipped, not guessed at).
    """
    from app.models import AWSAccount, SpendDaily  # local import: separate deployable, see module docstring

    account_rows = session.execute(
        select(AWSAccount.id, AWSAccount.aws_account_id).where(AWSAccount.org_id == org_id)
    ).all()
    account_id_by_aws_id = {aws_account_id: internal_id for internal_id, aws_account_id in account_rows}

    written = 0
    for record in spend_records:
        internal_account_id = account_id_by_aws_id.get(record.usage_account_id)
        if internal_account_id is None:
            continue

        stmt = pg_insert(SpendDaily).values(
            org_id=org_id,
            account_id=internal_account_id,
            usage_date=record.usage_date,
            service=record.service,
            unblended_cost=record.unblended_cost,
            amortized_cost=record.amortized_cost,
            currency=record.currency,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["org_id", "account_id", "usage_date", "service"],
            set_={
                "unblended_cost": stmt.excluded.unblended_cost,
                "amortized_cost": stmt.excluded.amortized_cost,
                "currency": stmt.excluded.currency,
            },
        )
        session.execute(stmt)
        written += 1

    return written
