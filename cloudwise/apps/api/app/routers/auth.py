from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from .. import security
from ..database import SessionLocal, org_scoped_session
from ..deps import get_current_user
from ..models import Organization, User
from ..schemas import LoginRequest, RegisterRequest, TokenResponse, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest) -> TokenResponse:
    session: Session = SessionLocal()
    try:
        # Email uniqueness has to be checked before any org exists for this
        # signup, so this is the one place a query runs without an org_id in
        # scope — allowed only via the narrow allow_login_lookup RLS policy.
        session.execute(text("SELECT set_config('app.allow_login_lookup', 'true', true)"))
        existing = session.execute(select(User).where(User.email == payload.email)).scalar_one_or_none()
        if existing is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

        org = Organization(name=payload.org_name)
        session.add(org)
        session.flush()  # assign org.id

        session.execute(text("SELECT set_config('app.current_org_id', :org_id, true)"), {"org_id": str(org.id)})
        user = User(
            org_id=org.id,
            email=payload.email,
            password_hash=security.hash_password(payload.password),
            role="owner",
        )
        session.add(user)
        session.flush()

        token = security.create_access_token(str(user.id), str(org.id), user.role)
        session.commit()
        return TokenResponse(access_token=token)
    except HTTPException:
        session.rollback()
        raise
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest) -> TokenResponse:
    with org_scoped_session(org_id=None, allow_login_lookup=True) as session:
        user = session.execute(select(User).where(User.email == payload.email)).scalar_one_or_none()
        if user is None or not security.verify_password(payload.password, user.password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
        token = security.create_access_token(str(user.id), str(user.org_id), user.role)
        return TokenResponse(access_token=token)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> User:
    return user
