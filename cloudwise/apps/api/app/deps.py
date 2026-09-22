import uuid
from typing import Generator

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWTError
from sqlalchemy.orm import Session

from . import security
from .database import org_scoped_session
from .models import User

bearer_scheme = HTTPBearer()


def get_token_payload(creds: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> dict:
    try:
        return security.decode_access_token(creds.credentials)
    except PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")


def get_db(payload: dict = Depends(get_token_payload)) -> Generator[Session, None, None]:
    # Every authenticated request's DB session is scoped to the org_id carried
    # in its own JWT — this is what makes the RLS policies in db/init.sql bite.
    with org_scoped_session(org_id=payload["org_id"]) as session:
        yield session


def get_current_user(payload: dict = Depends(get_token_payload), db: Session = Depends(get_db)) -> User:
    user = db.get(User, uuid.UUID(payload["sub"]))
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user
