"""User accounts and role-based access control (RBAC)."""
from __future__ import annotations

import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Enum, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    DOCTOR = "doctor"
    NURSE = "nurse"
    PATIENT = "patient"


class LanguagePref(str, enum.Enum):
    FA = "fa"
    EN = "en"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(128), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role", values_callable=lambda enum_cls: [e.value for e in enum_cls]),
        nullable=False,
        index=True,
    )

    email: Mapped[Optional[str]] = mapped_column(String(255), unique=True, nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # values_callable: SQLAlchemy's Enum type binds the Python member's
    # .name ("EN") by default, not .value ("en") -- but the Postgres enum
    # type this migrates against only accepts the lowercase .value labels.
    # Without this, every INSERT/UPDATE on this column fails.
    language_pref: Mapped[LanguagePref] = mapped_column(
        Enum(LanguagePref, name="language_pref", values_callable=lambda enum_cls: [e.value for e in enum_cls]),
        default=LanguagePref.EN,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # relationships
    patient_profile: Mapped[Optional["Patient"]] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    audit_logs: Mapped[list["AuditLog"]] = relationship(back_populates="user")

    # Flask-Login required interface
    @property
    def is_authenticated(self) -> bool:
        return True

    @property
    def is_anonymous(self) -> bool:
        return False

    def get_id(self) -> str:
        return str(self.id)

    def has_role(self, *roles: UserRole) -> bool:
        return self.role in roles

    def __repr__(self) -> str:
        return f"<User id={self.id} username={self.username!r} role={self.role}>"
