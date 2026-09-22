from typing import Any, Dict, Tuple

from sqlalchemy import select, text

from .database import SessionLocal
from .models import Organization, User

# Clerk's default organization roles. Map to CloudWise's own role enum
# (db/init.sql: owner/admin/approver/viewer) — least privilege by default;
# an org:admin becomes an "admin" here, everyone else starts as "viewer" and
# needs an explicit promotion (not yet built) to approve change requests.
CLERK_ROLE_MAP = {"org:admin": "admin"}
DEFAULT_ROLE_FOR_NEW_MEMBER = "viewer"
DEFAULT_ROLE_FOR_FIRST_USER_IN_ORG = "owner"


def get_or_create_org_and_user(identity: Dict[str, Any]) -> Tuple[Organization, User]:
    """Resolves a verified Clerk identity to CloudWise's internal org/user
    rows, creating them on first sight. This is the only place that creates
    an Organization or a User outside of a test fixture.
    """
    session = SessionLocal()
    try:
        # Organizations has no RLS (it isn't itself org-scoped data), so this
        # lookup needs no special policy. The users lookup below does.
        org = session.execute(
            select(Organization).where(Organization.clerk_org_id == identity["clerk_org_id"])
        ).scalar_one_or_none()
        if org is None:
            org = Organization(clerk_org_id=identity["clerk_org_id"], name=identity["org_name"])
            session.add(org)
            session.flush()

        session.execute(text("SELECT set_config('app.current_org_id', :org_id, true)"), {"org_id": str(org.id)})
        session.execute(text("SELECT set_config('app.allow_provisioning_lookup', 'true', true)"))

        user = session.execute(
            select(User).where(User.clerk_user_id == identity["clerk_user_id"])
        ).scalar_one_or_none()
        if user is None:
            is_first_user_in_org = (
                session.execute(select(User).where(User.org_id == org.id)).first() is None
            )
            role = (
                DEFAULT_ROLE_FOR_FIRST_USER_IN_ORG
                if is_first_user_in_org
                else CLERK_ROLE_MAP.get(identity.get("org_role") or "", DEFAULT_ROLE_FOR_NEW_MEMBER)
            )
            user = User(
                org_id=org.id,
                clerk_user_id=identity["clerk_user_id"],
                email=identity["email"],
                role=role,
            )
            session.add(user)
            session.flush()

        session.commit()
        return org, user
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
