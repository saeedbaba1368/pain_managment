"""
Audit logging. Every read/write of clinical data should go through log_action()
or the @audited decorator so there's a durable trail of who touched what.
"""
from __future__ import annotations

import functools
from typing import Any, Callable, Optional

from sqlalchemy.orm import Session

from models.audit_log import AuditLog


def log_action(
    db: Session,
    *,
    user_id: Optional[int],
    action: str,
    table_name: str,
    record_id: Optional[int] = None,
    ip_address: Optional[str] = None,
    details: Optional[dict] = None,
    commit: bool = False,
) -> AuditLog:
    """Write one audit trail row.

    `action` should be one of CREATE/READ/UPDATE/DELETE/LOGIN/LOGOUT/EXPORT/LOGIN_FAILED.
    Does not commit by default — callers usually want this in the same transaction
    as the change it's auditing (use session_scope, which commits atomically).
    """
    entry = AuditLog(
        user_id=user_id,
        action=action,
        table_name=table_name,
        record_id=record_id,
        ip_address=ip_address,
        details=details,
    )
    db.add(entry)
    db.flush()
    if commit:
        db.commit()
    return entry


def audited(action: str, table_name: str) -> Callable:
    """Decorator for service-layer functions that mutate clinical data.

    Expects the wrapped function's first positional arg to be a `db: Session`
    and to return an object with an `.id` attribute (the affected record).
    Pulls the current user from flask_login if available; falls back to None
    (e.g. when called from a script or seed job).

    Usage:
        @audited("UPDATE", "pain_records")
        def update_pain_record(db, record_id, **changes): ...
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(db: Session, *args, **kwargs) -> Any:
            result = func(db, *args, **kwargs)

            user_id = None
            ip_address = None
            try:
                from flask import request
                from flask_login import current_user

                if current_user and current_user.is_authenticated:
                    user_id = current_user.id
                ip_address = request.remote_addr
            except Exception:
                pass  # running outside a request context (script/seed/API) — audit with no actor

            record_id = getattr(result, "id", None)
            log_action(
                db,
                user_id=user_id,
                action=action,
                table_name=table_name,
                record_id=record_id,
                ip_address=ip_address,
            )
            return result

        return wrapper

    return decorator
