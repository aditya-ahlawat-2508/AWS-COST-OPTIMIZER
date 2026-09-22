from datetime import date

from sqlalchemy import select, text

from app.database import org_scoped_session
from app.models import AWSAccount, Organization, SpendDaily
from services.cur.loader import upsert_spend_daily
from services.cur.parser import DailyServiceSpend


def _make_org_and_account(aws_account_id: str):
    with org_scoped_session(org_id=None) as session:
        org = Organization(name="Acme")
        session.add(org)
        session.flush()
        org_id = org.id

    with org_scoped_session(org_id=str(org_id)) as session:
        account = AWSAccount(
            org_id=org_id,
            aws_account_id=aws_account_id,
            role_arn=f"arn:aws:iam::{aws_account_id}:role/CloudWiseReadOnly",
            external_id="ext-1",
        )
        session.add(account)
        session.flush()
        account_id = account.id

    return org_id, account_id


def test_upsert_writes_spend_for_connected_account():
    org_id, account_id = _make_org_and_account("111111111111")
    record = DailyServiceSpend(
        usage_account_id="111111111111",
        usage_date=date(2026, 9, 1),
        service="AmazonEC2",
        unblended_cost=12.5,
        amortized_cost=10.0,
        currency="USD",
    )

    with org_scoped_session(org_id=str(org_id)) as session:
        written = upsert_spend_daily(session, org_id, [record])
        assert written == 1

    with org_scoped_session(org_id=str(org_id)) as session:
        rows = session.execute(select(SpendDaily).where(SpendDaily.org_id == org_id)).scalars().all()
        assert len(rows) == 1
        assert rows[0].account_id == account_id
        assert float(rows[0].unblended_cost) == 12.5
        assert float(rows[0].amortized_cost) == 10.0


def test_upsert_skips_records_for_unconnected_accounts():
    org_id, _account_id = _make_org_and_account("111111111111")
    record = DailyServiceSpend(
        usage_account_id="999999999999",  # not connected to this org
        usage_date=date(2026, 9, 1),
        service="AmazonEC2",
        unblended_cost=5.0,
        amortized_cost=5.0,
        currency="USD",
    )

    with org_scoped_session(org_id=str(org_id)) as session:
        written = upsert_spend_daily(session, org_id, [record])
        assert written == 0


def test_upsert_is_idempotent_on_reingestion():
    org_id, _account_id = _make_org_and_account("111111111111")
    record_v1 = DailyServiceSpend(
        usage_account_id="111111111111",
        usage_date=date(2026, 9, 1),
        service="AmazonEC2",
        unblended_cost=10.0,
        amortized_cost=10.0,
        currency="USD",
    )
    record_v2 = DailyServiceSpend(
        usage_account_id="111111111111",
        usage_date=date(2026, 9, 1),
        service="AmazonEC2",
        unblended_cost=15.0,  # corrected/updated figure on re-export
        amortized_cost=15.0,
        currency="USD",
    )

    with org_scoped_session(org_id=str(org_id)) as session:
        upsert_spend_daily(session, org_id, [record_v1])

    with org_scoped_session(org_id=str(org_id)) as session:
        upsert_spend_daily(session, org_id, [record_v2])

    with org_scoped_session(org_id=str(org_id)) as session:
        rows = session.execute(select(SpendDaily).where(SpendDaily.org_id == org_id)).scalars().all()
        assert len(rows) == 1
        assert float(rows[0].unblended_cost) == 15.0


def test_spend_daily_is_org_scoped_by_rls():
    org_a_id, _ = _make_org_and_account("111111111111")
    org_b_id, _ = _make_org_and_account("222222222222")

    with org_scoped_session(org_id=str(org_a_id)) as session:
        upsert_spend_daily(
            session,
            org_a_id,
            [
                DailyServiceSpend(
                    usage_account_id="111111111111",
                    usage_date=date(2026, 9, 1),
                    service="AmazonEC2",
                    unblended_cost=1.0,
                    amortized_cost=1.0,
                    currency="USD",
                )
            ],
        )

    with org_scoped_session(org_id=str(org_b_id)) as session:
        rows = session.execute(text("SELECT service FROM spend_daily")).scalars().all()
        assert rows == []
