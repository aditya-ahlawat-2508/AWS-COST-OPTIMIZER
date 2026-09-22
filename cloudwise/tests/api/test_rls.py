"""Proves tenant isolation at the database layer itself, independent of any
app-level `WHERE org_id = ...` filter. If Postgres RLS (db/init.sql) weren't
enforcing this, a raw SELECT * with no filter would return both orgs' rows.
"""
from sqlalchemy import text

from app.database import org_scoped_session
from app.models import AWSAccount, Organization


def test_rls_blocks_cross_org_select_even_without_app_filter():
    with org_scoped_session(org_id=None) as session:
        org_a = Organization(name="Org A")
        org_b = Organization(name="Org B")
        session.add_all([org_a, org_b])
        session.flush()
        org_a_id, org_b_id = org_a.id, org_b.id

    with org_scoped_session(org_id=str(org_a_id)) as session:
        session.add(
            AWSAccount(
                org_id=org_a_id,
                aws_account_id="111111111111",
                role_arn="arn:aws:iam::111111111111:role/x",
                external_id="e1",
            )
        )

    with org_scoped_session(org_id=str(org_b_id)) as session:
        session.add(
            AWSAccount(
                org_id=org_b_id,
                aws_account_id="222222222222",
                role_arn="arn:aws:iam::222222222222:role/x",
                external_id="e2",
            )
        )

    with org_scoped_session(org_id=str(org_a_id)) as session:
        rows = session.execute(text("SELECT aws_account_id FROM aws_accounts")).scalars().all()
        assert rows == ["111111111111"]

    with org_scoped_session(org_id=str(org_b_id)) as session:
        rows = session.execute(text("SELECT aws_account_id FROM aws_accounts")).scalars().all()
        assert rows == ["222222222222"]


def test_no_org_context_means_no_rows():
    with org_scoped_session(org_id=None) as session:
        org = Organization(name="Org C")
        session.add(org)
        session.flush()
        org_id = org.id

    with org_scoped_session(org_id=str(org_id)) as session:
        session.add(
            AWSAccount(
                org_id=org_id,
                aws_account_id="333333333333",
                role_arn="arn:aws:iam::333333333333:role/x",
                external_id="e3",
            )
        )

    # No app.current_org_id set at all -> RLS default-denies everything.
    with org_scoped_session(org_id=None) as session:
        rows = session.execute(text("SELECT aws_account_id FROM aws_accounts")).scalars().all()
        assert rows == []
