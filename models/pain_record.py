"""Pain records (VAS scores) and interactive body-map points."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base


class PainRecord(Base):
    __tablename__ = "pain_records"
    __table_args__ = (
        CheckConstraint("vas_score >= 0 AND vas_score <= 10", name="ck_pain_records_vas_range"),
        Index("ix_pain_records_patient_timestamp", "patient_id", "timestamp"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"), index=True, nullable=False
    )
    vas_score: Mapped[int] = mapped_column(Integer, nullable=False)
    body_locations: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    pain_quality: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True, comment="e.g. burning, stabbing, throbbing"
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    recorded_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    self_reported: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    patient: Mapped["Patient"] = relationship(back_populates="pain_records")
    recorder: Mapped[Optional["User"]] = relationship(foreign_keys=[recorded_by])
    body_map_points: Mapped[list["BodyMapPoint"]] = relationship(
        back_populates="pain_record", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<PainRecord id={self.id} patient_id={self.patient_id} vas={self.vas_score}>"


class BodyMapPoint(Base):
    """Individual clicked point on the SVG body map for a given pain record."""

    __tablename__ = "body_map_points"

    id: Mapped[int] = mapped_column(primary_key=True)
    pain_record_id: Mapped[int] = mapped_column(
        ForeignKey("pain_records.id", ondelete="CASCADE"), index=True, nullable=False
    )
    body_part: Mapped[str] = mapped_column(String(64), nullable=False)
    x_coord: Mapped[float] = mapped_column(Float, nullable=False, comment="normalized 0-1 SVG x")
    y_coord: Mapped[float] = mapped_column(Float, nullable=False, comment="normalized 0-1 SVG y")
    intensity: Mapped[int] = mapped_column(Integer, nullable=False, comment="0-10, drives color gradient")

    pain_record: Mapped["PainRecord"] = relationship(back_populates="body_map_points")

    def __repr__(self) -> str:
        return f"<BodyMapPoint id={self.id} part={self.body_part} intensity={self.intensity}>"
