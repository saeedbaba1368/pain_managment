"""Patient demographic and contact records.

Sensitive PII (national_code, phone, address) is stored via EncryptedString,
a custom SQLAlchemy TypeDecorator defined in core/security.py that transparently
encrypts/decrypts using the app's Fernet key. See core/security.py.
"""
from __future__ import annotations

import enum
from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, DateTime, Enum, Float, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base
from core.security import EncryptedString


class Gender(str, enum.Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"


class BloodType(str, enum.Enum):
    A_POS = "A+"
    A_NEG = "A-"
    B_POS = "B+"
    B_NEG = "B-"
    AB_POS = "AB+"
    AB_NEG = "AB-"
    O_POS = "O+"
    O_NEG = "O-"
    UNKNOWN = "unknown"


class Patient(Base):
    __tablename__ = "patients"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), unique=True)

    national_code: Mapped[str] = mapped_column(EncryptedString(64), unique=True, nullable=False)
    first_name: Mapped[str] = mapped_column(String(64), nullable=False)
    last_name: Mapped[str] = mapped_column(String(64), nullable=False)
    birth_date: Mapped[date] = mapped_column(Date, nullable=False)
    gender: Mapped[Gender] = mapped_column(
        Enum(Gender, name="gender", values_callable=lambda enum_cls: [e.value for e in enum_cls]),
        nullable=False,
    )

    phone: Mapped[str] = mapped_column(EncryptedString(64), nullable=False)
    address: Mapped[Optional[str]] = mapped_column(EncryptedString(512), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(128), index=True, nullable=True)
    latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    emergency_contact: Mapped[Optional[str]] = mapped_column(EncryptedString(255), nullable=True)
    blood_type: Mapped[BloodType] = mapped_column(
        Enum(BloodType, name="blood_type", values_callable=lambda enum_cls: [e.value for e in enum_cls]),
        default=BloodType.UNKNOWN,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # relationships
    user: Mapped[Optional["User"]] = relationship(back_populates="patient_profile")
    diagnoses: Mapped[list["Diagnosis"]] = relationship(back_populates="patient", cascade="all, delete-orphan")
    pain_records: Mapped[list["PainRecord"]] = relationship(back_populates="patient", cascade="all, delete-orphan")
    medications: Mapped[list["Medication"]] = relationship(back_populates="patient", cascade="all, delete-orphan")
    vital_signs: Mapped[list["VitalSigns"]] = relationship(back_populates="patient", cascade="all, delete-orphan")
    treatments: Mapped[list["Treatment"]] = relationship(back_populates="patient", cascade="all, delete-orphan")
    appointments: Mapped[list["Appointment"]] = relationship(
        back_populates="patient", cascade="all, delete-orphan", foreign_keys="Appointment.patient_id"
    )

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    def __repr__(self) -> str:
        return f"<Patient id={self.id} name={self.full_name!r}>"
