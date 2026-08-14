"""
Security primitives: password hashing, at-rest field encryption for PII,
JWT issuance/verification for the REST API, and RBAC guards for Dash callbacks.
"""
from __future__ import annotations

import functools
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Optional

import bcrypt
from cryptography.fernet import Fernet, InvalidToken
from jose import JWTError, jwt
from sqlalchemy import Text
from sqlalchemy.types import TypeDecorator

from config import settings

# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------


def hash_password(plain_password: str) -> str:
    """Hash a password with bcrypt. Store only the result."""
    salt = bcrypt.gensalt(rounds=settings.BCRYPT_ROUNDS)
    return bcrypt.hashpw(plain_password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Constant-time password check against a stored bcrypt hash."""
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        # malformed hash — never let this raise into an auth code path
        return False


# ---------------------------------------------------------------------------
# Field-level encryption for PII columns (national_code, phone, address, ...)
# ---------------------------------------------------------------------------

_fernet = Fernet(settings.FIELD_ENCRYPTION_KEY.encode("utf-8"))


class EncryptedString(TypeDecorator):
    """SQLAlchemy column type that transparently encrypts/decrypts a string
    using Fernet (AES-128-CBC + HMAC). Stored as TEXT in Postgres.

    Usage: mapped_column(EncryptedString(255))
    """

    impl = Text
    cache_ok = True

    def process_bind_param(self, value: Optional[str], dialect: Any) -> Optional[str]:
        if value is None:
            return None
        return _fernet.encrypt(value.encode("utf-8")).decode("utf-8")

    def process_result_value(self, value: Optional[str], dialect: Any) -> Optional[str]:
        if value is None:
            return None
        try:
            return _fernet.decrypt(value.encode("utf-8")).decode("utf-8")
        except InvalidToken:
            # Data predates encryption or the key rotated without re-encrypting.
            # Fail loud rather than silently leaking ciphertext into the UI.
            raise ValueError("Unable to decrypt field — check FIELD_ENCRYPTION_KEY.")


def generate_encryption_key() -> str:
    """Utility for ops: `python -c 'from core.security import generate_encryption_key as g; print(g())'`"""
    return Fernet.generate_key().decode("utf-8")


# ---------------------------------------------------------------------------
# JWT (used by the FastAPI REST service, not the Dash session)
# ---------------------------------------------------------------------------


def create_access_token(subject: str, role: str, expires_delta: Optional[timedelta] = None) -> str:
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload = {"sub": subject, "role": role, "exp": expire, "type": "access"}
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {"sub": subject, "exp": expire, "type": "refresh"}
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """Raises JWTError on invalid/expired token — callers must catch it."""
    try:
        return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except JWTError as exc:
        raise JWTError(f"Invalid or expired token: {exc}") from exc


# ---------------------------------------------------------------------------
# RBAC guard for Dash callbacks (FastAPI has its own dependency, see api/auth.py)
# ---------------------------------------------------------------------------


class AccessDenied(Exception):
    """Raised when a logged-in user's role doesn't permit an action."""


def require_role(*allowed_roles: str) -> Callable:
    """Decorator for Dash callback functions. Expects flask_login.current_user
    to be available in the request context.

    Usage:
        @require_role("admin", "doctor")
        def update_patient(...): ...
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            from flask_login import current_user  # local import avoids Dash/Flask app-context issues at import time

            if not current_user.is_authenticated:
                raise AccessDenied("Login required.")
            if current_user.role.value not in allowed_roles:
                raise AccessDenied(
                    f"Role '{current_user.role.value}' is not permitted to perform this action."
                )
            return func(*args, **kwargs)

        return wrapper

    return decorator
