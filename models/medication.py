"""Medications, dose adherence logs, and reported side effects."""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base


class Medication(Base):
    __tablename__ = "medications"
    __table_args__ = (Index("ix_medications_patient_opioid", "patient_id", "is_opioid"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"), index=True, nullable=False
    )
    drug_name: Mapped[str] = mapped_column(String(128), nullable=False)
    dosage: Mapped[str] = mapped_column(String(64), nullable=False)
    frequency: Mapped[str] = mapped_column(String(64), nullable=False, comment="e.g. 'every 8 hours'")
    route: Mapped[str] = mapped_column(String(32), nullable=False, comment="oral/IV/topical/etc.")
    is_opioid: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    prescribed_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    patient: Mapped["Patient"] = relationship(back_populates="medications")
    prescriber: Mapped[Optional["User"]] = relationship(foreign_keys=[prescribed_by])
    logs: Mapped[list["MedicationLog"]] = relationship(back_populates="medication", cascade="all, delete-orphan")
    side_effects: Mapped[list["SideEffect"]] = relationship(
        back_populates="medication", cascade="all, delete-orphan"
    )

    @property
    def is_active(self) -> bool:
        return self.end_date is None or self.end_date >= date.today()

    def __repr__(self) -> str:
        return f"<Medication id={self.id} drug={self.drug_name!r} opioid={self.is_opioid}>"


class MedicationLog(Base):
    """Dose-taken adherence log, used to drive missed-dose alerts."""

    __tablename__ = "medication_logs"
    __table_args__ = (Index("ix_medication_logs_med_taken_at", "medication_id", "taken_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    medication_id: Mapped[int] = mapped_column(
        ForeignKey("medications.id", ondelete="CASCADE"), index=True, nullable=False
    )
    taken_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    taken: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    missed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    medication: Mapped["Medication"] = relationship(back_populates="logs")

    def __repr__(self) -> str:
        return f"<MedicationLog id={self.id} medication_id={self.medication_id} taken={self.taken}>"


class SideEffect(Base):
    __tablename__ = "side_effects"

    id: Mapped[int] = mapped_column(primary_key=True)
    medication_id: Mapped[int] = mapped_column(
        ForeignKey("medications.id", ondelete="CASCADE"), index=True, nullable=False
    )
    patient_id: Mapped[int] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"), index=True, nullable=False
    )
    effect_description: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False, comment="mild/moderate/severe")
    reported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    medication: Mapped["Medication"] = relationship(back_populates="side_effects")
    patient: Mapped["Patient"] = relationship()

    def __repr__(self) -> str:
        return f"<SideEffect id={self.id} severity={self.severity}>"
