"""
Import every model here so Base.metadata sees the full schema —
required for Alembic autogenerate and for relationship() string
lookups (e.g. Mapped["Patient"]) to resolve correctly.
"""
from core.database import Base  # noqa: F401

from models.user import User, UserRole, LanguagePref  # noqa: F401
from models.patient import Patient, Gender, BloodType  # noqa: F401
from models.diagnosis import Diagnosis, PainType  # noqa: F401
from models.pain_record import PainRecord, BodyMapPoint  # noqa: F401
from models.medication import Medication, MedicationLog, SideEffect  # noqa: F401
from models.vital_signs import VitalSigns  # noqa: F401
from models.treatment import Treatment, TreatmentType  # noqa: F401
from models.appointment import Appointment, AppointmentStatus  # noqa: F401
from models.audit_log import AuditLog  # noqa: F401

__all__ = [
    "Base",
    "User", "UserRole", "LanguagePref",
    "Patient", "Gender", "BloodType",
    "Diagnosis", "PainType",
    "PainRecord", "BodyMapPoint",
    "Medication", "MedicationLog", "SideEffect",
    "VitalSigns",
    "Treatment", "TreatmentType",
    "Appointment", "AppointmentStatus",
    "AuditLog",
]
