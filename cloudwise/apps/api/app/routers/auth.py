from fastapi import APIRouter, Depends

from ..deps import get_current_user
from ..models import User
from ..schemas import UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> User:
    # Hitting this (or any authenticated endpoint) with a valid Clerk token is
    # what provisions the org/user row on first sight — see app/deps.py.
    return user
