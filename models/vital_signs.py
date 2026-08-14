"""Vital signs recordings."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base


class VitalSigns(Base):
    __tablename__ = "vital_signs"
    __table_args__ = (Index("ix_vital_signs_patient_recorded_at", "patient_id", "recorded_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"), index=True, nullable=False
    )
    systolic_bp: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    diastolic_bp: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    heart_rate: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    temperature: Mapped[Optional[float]] = mapped_column(Float, nullable=True, comment="Celsius")
    respiratory_rate: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    o2_saturation: Mapped[Optional[float]] = mapped_column(Float, nullable=True, comment="percent")
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    recorded_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))

    patient: Mapped["Patient"] = relationship(back_populates="vital_signs")
    recorder: Mapped[Optional["User"]] = relationship(foreign_keys=[recorded_by])

    def __repr__(self) -> str:
        return f"<VitalSigns id={self.id} patient_id={self.patient_id} hr={self.heart_rate}>"
