"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-08-13
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- users ---
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(64), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(128), nullable=False),
        sa.Column(
            "role",
            sa.Enum("admin", "doctor", "nurse", "patient", name="user_role"),
            nullable=False,
        ),
        sa.Column("email", sa.String(255), unique=True, nullable=True),
        sa.Column("phone", sa.String(32), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "language_pref",
            sa.Enum("fa", "en", name="language_pref"),
            nullable=False,
            server_default="en",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("last_login", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_users_username", "users", ["username"])
    op.create_index("ix_users_role", "users", ["role"])

    # --- patients ---
    op.create_table(
        "patients",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), unique=True),
        sa.Column("national_code", sa.String(64), nullable=False, unique=True),
        sa.Column("first_name", sa.String(64), nullable=False),
        sa.Column("last_name", sa.String(64), nullable=False),
        sa.Column("birth_date", sa.Date(), nullable=False),
        sa.Column("gender", sa.Enum("male", "female", "other", name="gender"), nullable=False),
        sa.Column("phone", sa.String(64), nullable=False),
        sa.Column("address", sa.String(512), nullable=True),
        sa.Column("city", sa.String(128), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("emergency_contact", sa.String(255), nullable=True),
        sa.Column(
            "blood_type",
            sa.Enum("A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-", "unknown", name="blood_type"),
            nullable=False,
            server_default="unknown",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_patients_city", "patients", ["city"])

    # --- diagnoses ---
    op.create_table(
        "diagnoses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "patient_id", sa.Integer(), sa.ForeignKey("patients.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("icd10_code", sa.String(16), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "pain_type",
            sa.Enum("chronic", "acute", "post_surgical", "cancer", name="pain_type"),
            nullable=False,
        ),
        sa.Column("diagnosis_date", sa.Date(), nullable=False),
        sa.Column("doctor_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_diagnoses_patient_id", "diagnoses", ["patient_id"])
    op.create_index("ix_diagnoses_icd10_code", "diagnoses", ["icd10_code"])
    op.create_index("ix_diagnoses_pain_type", "diagnoses", ["pain_type"])

    # --- pain_records ---
    op.create_table(
        "pain_records",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "patient_id", sa.Integer(), sa.ForeignKey("patients.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("vas_score", sa.Integer(), nullable=False),
        sa.Column("body_locations", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("pain_quality", sa.String(64), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("recorded_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("self_reported", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.CheckConstraint("vas_score >= 0 AND vas_score <= 10", name="ck_pain_records_vas_range"),
    )
    op.create_index("ix_pain_records_patient_id", "pain_records", ["patient_id"])
    op.create_index(
        "ix_pain_records_patient_timestamp", "pain_records", ["patient_id", "timestamp"]
    )

    # --- body_map_points ---
    op.create_table(
        "body_map_points",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "pain_record_id",
            sa.Integer(),
            sa.ForeignKey("pain_records.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("body_part", sa.String(64), nullable=False),
        sa.Column("x_coord", sa.Float(), nullable=False),
        sa.Column("y_coord", sa.Float(), nullable=False),
        sa.Column("intensity", sa.Integer(), nullable=False),
    )
    op.create_index("ix_body_map_points_pain_record_id", "body_map_points", ["pain_record_id"])

    # --- medications ---
    op.create_table(
        "medications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "patient_id", sa.Integer(), sa.ForeignKey("patients.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("drug_name", sa.String(128), nullable=False),
        sa.Column("dosage", sa.String(64), nullable=False),
        sa.Column("frequency", sa.String(64), nullable=False),
        sa.Column("route", sa.String(32), nullable=False),
        sa.Column("is_opioid", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("prescribed_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_medications_patient_id", "medications", ["patient_id"])
    op.create_index("ix_medications_is_opioid", "medications", ["is_opioid"])
    op.create_index("ix_medications_patient_opioid", "medications", ["patient_id", "is_opioid"])

    # --- medication_logs ---
    op.create_table(
        "medication_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "medication_id",
            sa.Integer(),
            sa.ForeignKey("medications.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("taken_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("taken", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("missed", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index("ix_medication_logs_medication_id", "medication_logs", ["medication_id"])
    op.create_index(
        "ix_medication_logs_med_taken_at", "medication_logs", ["medication_id", "taken_at"]
    )

    # --- side_effects ---
    op.create_table(
        "side_effects",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "medication_id",
            sa.Integer(),
            sa.ForeignKey("medications.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "patient_id", sa.Integer(), sa.ForeignKey("patients.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("effect_description", sa.Text(), nullable=False),
        sa.Column("severity", sa.String(16), nullable=False),
        sa.Column("reported_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_side_effects_medication_id", "side_effects", ["medication_id"])
    op.create_index("ix_side_effects_patient_id", "side_effects", ["patient_id"])

    # --- vital_signs ---
    op.create_table(
        "vital_signs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "patient_id", sa.Integer(), sa.ForeignKey("patients.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("systolic_bp", sa.Integer(), nullable=True),
        sa.Column("diastolic_bp", sa.Integer(), nullable=True),
        sa.Column("heart_rate", sa.Integer(), nullable=True),
        sa.Column("temperature", sa.Float(), nullable=True),
        sa.Column("respiratory_rate", sa.Integer(), nullable=True),
        sa.Column("o2_saturation", sa.Float(), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("recorded_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
    )
    op.create_index("ix_vital_signs_patient_id", "vital_signs", ["patient_id"])
    op.create_index(
        "ix_vital_signs_patient_recorded_at", "vital_signs", ["patient_id", "recorded_at"]
    )

    # --- treatments ---
    op.create_table(
        "treatments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "patient_id", sa.Integer(), sa.ForeignKey("patients.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "treatment_type",
            sa.Enum("physical_therapy", "injection", "surgery", "medication", name="treatment_type"),
            nullable=False,
        ),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("outcome", sa.Text(), nullable=True),
        sa.Column("cost", sa.Numeric(10, 2), nullable=True),
        sa.Column("performed_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_treatments_patient_id", "treatments", ["patient_id"])
    op.create_index("ix_treatments_treatment_type", "treatments", ["treatment_type"])

    # --- appointments ---
    op.create_table(
        "appointments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "patient_id", sa.Integer(), sa.ForeignKey("patients.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("doctor_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration", sa.Integer(), nullable=False, server_default="30"),
        sa.Column(
            "status",
            sa.Enum("scheduled", "completed", "cancelled", "no_show", name="appointment_status"),
            nullable=False,
            server_default="scheduled",
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_appointments_patient_id", "appointments", ["patient_id"])
    op.create_index("ix_appointments_scheduled_at", "appointments", ["scheduled_at"])
    op.create_index("ix_appointments_status", "appointments", ["status"])
    op.create_index(
        "ix_appointments_doctor_scheduled_at", "appointments", ["doctor_id", "scheduled_at"]
    )

    # --- audit_logs ---
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("action", sa.String(32), nullable=False),
        sa.Column("table_name", sa.String(64), nullable=False),
        sa.Column("record_id", sa.Integer(), nullable=True),
        sa.Column("ip_address", postgresql.INET(), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("details", postgresql.JSONB(), nullable=True),
    )
    op.create_index("ix_audit_logs_table_record", "audit_logs", ["table_name", "record_id"])
    op.create_index("ix_audit_logs_user_timestamp", "audit_logs", ["user_id", "timestamp"])


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("appointments")
    op.drop_table("treatments")
    op.drop_table("vital_signs")
    op.drop_table("side_effects")
    op.drop_table("medication_logs")
    op.drop_table("medications")
    op.drop_table("body_map_points")
    op.drop_table("pain_records")
    op.drop_table("diagnoses")
    op.drop_table("patients")
    op.drop_table("users")

    # drop enum types explicitly (postgres doesn't cascade-drop them with drop_table)
    for enum_name in (
        "user_role",
        "language_pref",
        "gender",
        "blood_type",
        "pain_type",
        "treatment_type",
        "appointment_status",
    ):
        op.execute(f"DROP TYPE IF EXISTS {enum_name}")
