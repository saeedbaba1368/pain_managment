"""Authentication endpoints for the REST API (mobile app / third-party clients).

Separate from the Dash app's Flask-Login session in app.py — this issues
JWTs instead of a server-side session cookie.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from jose import JWTError
from sqlalchemy.orm import Session

from api.deps import audit, get_current_user, get_db, limiter
from config import settings
from core.security import create_access_token, create_refresh_token, decode_token, verify_password
from models import User
from api.schemas import RefreshRequest, Token, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=Token)
@limiter.limit(settings.RATE_LIMIT_LOGIN)
def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(OAuth2PasswordRequestForm),
    db: Session = Depends(get_db),
) -> Token:
    """OAuth2 password flow. Rate-limited more aggressively than other
    routes (see config.RATE_LIMIT_LOGIN) to slow down credential stuffing."""
    user = db.query(User).filter(User.username == form_data.username).first()

    if user is None or not user.is_active or not verify_password(form_data.password, user.password_hash):
        # Audit failed attempts too — useful for detecting brute-force patterns.
        audit(db, request, None, action="LOGIN_FAILED", table_name="users", details={"username": form_data.username})
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user.last_login = datetime.now(timezone.utc)
    db.add(user)
    db.commit()

    audit(db, request, user, action="LOGIN", table_name="users", record_id=user.id)

    return Token(
        access_token=create_access_token(subject=str(user.id), role=user.role.value),
        refresh_token=create_refresh_token(subject=str(user.id)),
    )


@router.post("/refresh", response_model=Token)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)) -> Token:
    """Exchange a valid refresh token for a new access/refresh pair."""
    try:
        decoded = decode_token(payload.refresh_token)
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token")

    if decoded.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not a refresh token")

    user = db.get(User, int(decoded["sub"]))
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User no longer active")

    return Token(
        access_token=create_access_token(subject=str(user.id), role=user.role.value),
        refresh_token=create_refresh_token(subject=str(user.id)),
    )


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user
