"""Treatments administered to patients (therapy, injections, surgery, etc.)."""
from __future__ import annotations

import enum
from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Numeric, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base


class TreatmentType(str, enum.Enum):
    PHYSICAL_THERAPY = "physical_therapy"
    INJECTION = "injection"
    SURGERY = "surgery"
    MEDICATION = "medication"


class Treatment(Base):
    __tablename__ = "treatments"

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"), index=True, nullable=False
    )
    treatment_type: Mapped[TreatmentType] = mapped_column(
        Enum(TreatmentType, name="treatment_type", values_callable=lambda enum_cls: [e.value for e in enum_cls]),
        nullable=False,
        index=True,
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    outcome: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    cost: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    performed_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    patient: Mapped["Patient"] = relationship(back_populates="treatments")
    performer: Mapped[Optional["User"]] = relationship(foreign_keys=[performed_by])

    def __repr__(self) -> str:
        return f"<Treatment id={self.id} type={self.treatment_type} patient_id={self.patient_id}>"
