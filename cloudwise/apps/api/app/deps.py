from typing import Generator

import jwt as pyjwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from . import clerk_auth
from .database import org_scoped_session
from .models import User
from .provisioning import get_or_create_org_and_user

bearer_scheme = HTTPBearer()


def get_current_identity(creds: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> dict:
    try:
        payload = clerk_auth.verify_clerk_token(creds.credentials)
        return clerk_auth.extract_identity(payload)
    except clerk_auth.NoActiveOrganization as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except pyjwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")


def get_current_user(identity: dict = Depends(get_current_identity)) -> User:
    # First authenticated request from a Clerk user/org CloudWise hasn't seen
    # creates the org + user row — there is no separate signup endpoint.
    _org, user = get_or_create_org_and_user(identity)
    return user


def get_db(user: User = Depends(get_current_user)) -> Generator[Session, None, None]:
    with org_scoped_session(org_id=str(user.org_id)) as session:
        yield session
