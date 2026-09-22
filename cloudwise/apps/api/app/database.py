from contextlib import contextmanager
from typing import Generator, Optional

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from .config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


@contextmanager
def org_scoped_session(
    org_id: Optional[str] = None, allow_login_lookup: bool = False
) -> Generator[Session, None, None]:
    """Open a DB session whose transaction carries the tenant context that the
    Postgres RLS policies in db/init.sql check on every row. This is the
    single choke point where org_id must be set correctly — get it wrong here
    and RLS denies the query outright rather than silently leaking rows.
    """
    session = SessionLocal()
    try:
        # SET LOCAL doesn't accept bind parameters over the extended protocol;
        # set_config() is a normal function call and does.
        if org_id is not None:
            session.execute(
                text("SELECT set_config('app.current_org_id', :org_id, true)"), {"org_id": str(org_id)}
            )
        session.execute(
            text("SELECT set_config('app.allow_login_lookup', :flag, true)"),
            {"flag": "true" if allow_login_lookup else "false"},
        )
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
