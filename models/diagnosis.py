"""Patient diagnoses (ICD-10 coded)."""
from __future__ import annotations

import enum
from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base


class PainType(str, enum.Enum):
    CHRONIC = "chronic"
    ACUTE = "acute"
    POST_SURGICAL = "post_surgical"
    CANCER = "cancer"


class Diagnosis(Base):
    __tablename__ = "diagnoses"

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"), index=True, nullable=False
    )
    icd10_code: Mapped[str] = mapped_column(String(16), index=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    pain_type: Mapped[PainType] = mapped_column(
        Enum(PainType, name="pain_type", values_callable=lambda enum_cls: [e.value for e in enum_cls]),
        nullable=False,
        index=True,
    )
    diagnosis_date: Mapped[date] = mapped_column(Date, nullable=False)
    doctor_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    patient: Mapped["Patient"] = relationship(back_populates="diagnoses")
    doctor: Mapped[Optional["User"]] = relationship(foreign_keys=[doctor_id])

    def __repr__(self) -> str:
        return f"<Diagnosis id={self.id} icd10={self.icd10_code} patient_id={self.patient_id}>"
