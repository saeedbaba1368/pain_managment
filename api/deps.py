"""
Shared FastAPI dependencies: DB session injection, JWT bearer auth, RBAC
guards, and a thin audit-logging helper. Mirrors core/security.py's
Flask-Login guards but adapted for a stateless token-based API.
"""
from __future__ import annotations

from typing import Generator, Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from core.audit import log_action
from core.database import SessionLocal
from core.security import decode_token
from models import Patient, User, UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# Keyed by client IP; slowapi reads settings.RATE_LIMIT_DEFAULT as the
# blanket limit and individual routes override it (e.g. login).
limiter = Limiter(key_func=get_remote_address)


def get_db() -> Generator[Session, None, None]:
    """Per-request DB session — FastAPI closes it via the generator teardown."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Decode the bearer token and load the corresponding active user."""
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
    except JWTError:
        raise credentials_error

    if payload.get("type") != "access":
        raise credentials_error

    user_id = payload.get("sub")
    if user_id is None:
        raise credentials_error

    user = db.get(User, int(user_id))
    if user is None or not user.is_active:
        raise credentials_error
    return user


def require_roles(*allowed_roles: UserRole):
    """Dependency factory — usage: `Depends(require_roles(UserRole.ADMIN, UserRole.DOCTOR))`."""

    def dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{current_user.role.value}' is not permitted to perform this action.",
            )
        return current_user

    return dependency


# Clinical staff who can act on behalf of any patient.
require_staff = require_roles(UserRole.ADMIN, UserRole.DOCTOR, UserRole.NURSE)
require_admin = require_roles(UserRole.ADMIN)
require_prescriber = require_roles(UserRole.ADMIN, UserRole.DOCTOR)


def resolve_patient_scope(
    patient_id: int,
    db: Session,
    current_user: User,
) -> Patient:
    """Loads the patient and enforces that a `patient`-role user can only
    ever touch their own record. Staff roles may access any patient.

    Raises 404 rather than 403 when a patient user requests someone else's
    record, so as not to leak which patient IDs exist.
    """
    patient = db.get(Patient, patient_id)
    if patient is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")

    if current_user.role == UserRole.PATIENT:
        if patient.user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")

    return patient


def client_ip(request: Request) -> Optional[str]:
    return request.client.host if request.client else None


def audit(
    db: Session,
    request: Request,
    current_user: Optional[User],
    action: str,
    table_name: str,
    record_id: Optional[int] = None,
    details: Optional[dict] = None,
) -> None:
    """Write one audit trail row and commit immediately (API requests are
    typically one DB operation per request, unlike the Dash session_scope
    pattern used elsewhere)."""
    log_action(
        db,
        user_id=current_user.id if current_user else None,
        action=action,
        table_name=table_name,
        record_id=record_id,
        ip_address=client_ip(request),
        details=details,
        commit=True,
    )
