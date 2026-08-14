"""
Pydantic schemas for the REST API.

Naming convention: <Model>Create (write payload), <Model>Update (partial
write payload), <Model>Out (response). Out schemas use from_attributes=True
so they can be built directly from SQLAlchemy ORM instances.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Generic, Optional, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_validator

from models.appointment import AppointmentStatus
from models.diagnosis import PainType
from models.patient import BloodType, Gender
from models.treatment import TreatmentType
from models.user import LanguagePref, UserRole

# ---------------------------------------------------------------------------
# Shared / generic
# ---------------------------------------------------------------------------

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    """Generic pagination envelope returned by every list endpoint."""

    items: list[T]
    total: int
    page: int
    page_size: int


class Message(BaseModel):
    detail: str


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    full_name: str
    role: UserRole
    email: Optional[str] = None
    phone: Optional[str] = None
    is_active: bool
    language_pref: LanguagePref
    last_login: Optional[datetime] = None


# ---------------------------------------------------------------------------
# Patients
# ---------------------------------------------------------------------------


class PatientCreate(BaseModel):
    national_code: str = Field(..., min_length=3, max_length=32)
    first_name: str = Field(..., min_length=1, max_length=64)
    last_name: str = Field(..., min_length=1, max_length=64)
    birth_date: date
    gender: Gender
    phone: str = Field(..., min_length=3, max_length=32)
    address: Optional[str] = None
    city: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    emergency_contact: Optional[str] = None
    blood_type: BloodType = BloodType.UNKNOWN
    user_id: Optional[int] = None

    @field_validator("birth_date")
    @classmethod
    def _not_in_future(cls, v: date) -> date:
        if v > date.today():
            raise ValueError("birth_date cannot be in the future")
        return v


class PatientUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    emergency_contact: Optional[str] = None
    blood_type: Optional[BloodType] = None


class PatientOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    national_code: str
    first_name: str
    last_name: str
    birth_date: date
    gender: Gender
    phone: str
    address: Optional[str] = None
    city: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    emergency_contact: Optional[str] = None
    blood_type: BloodType
    created_at: datetime


# ---------------------------------------------------------------------------
# Pain records
# ---------------------------------------------------------------------------


class BodyMapPointIn(BaseModel):
    body_part: str
    x_coord: float = Field(..., ge=0.0, le=1.0)
    y_coord: float = Field(..., ge=0.0, le=1.0)
    intensity: int = Field(..., ge=0, le=10)


class BodyMapPointOut(BodyMapPointIn):
    model_config = ConfigDict(from_attributes=True)
    id: int


class PainRecordCreate(BaseModel):
    patient_id: int
    vas_score: int = Field(..., ge=0, le=10)
    body_locations: list[str] = Field(default_factory=list)
    pain_quality: Optional[str] = None
    notes: Optional[str] = None
    self_reported: bool = False
    body_map_points: list[BodyMapPointIn] = Field(default_factory=list)


class PainRecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    patient_id: int
    vas_score: int
    body_locations: list[str]
    pain_quality: Optional[str] = None
    timestamp: datetime
    notes: Optional[str] = None
    recorded_by: Optional[int] = None
    self_reported: bool
    body_map_points: list[BodyMapPointOut] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Medications
# ---------------------------------------------------------------------------


class MedicationCreate(BaseModel):
    patient_id: int
    drug_name: str = Field(..., max_length=128)
    dosage: str = Field(..., max_length=64)
    frequency: str = Field(..., max_length=64)
    route: str = Field(..., max_length=32)
    is_opioid: bool = False
    start_date: date
    end_date: Optional[date] = None


class MedicationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    patient_id: int
    drug_name: str
    dosage: str
    frequency: str
    route: str
    is_opioid: bool
    start_date: date
    end_date: Optional[date] = None
    prescribed_by: Optional[int] = None
    is_active: bool


class MedicationLogCreate(BaseModel):
    taken_at: datetime
    taken: bool = True
    missed: bool = False


class MedicationLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    medication_id: int
    taken_at: datetime
    taken: bool
    missed: bool


class SideEffectCreate(BaseModel):
    medication_id: int
    patient_id: int
    effect_description: str
    severity: str = Field(..., pattern="^(mild|moderate|severe)$")


class SideEffectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    medication_id: int
    patient_id: int
    effect_description: str
    severity: str
    reported_at: datetime


# ---------------------------------------------------------------------------
# Vitals
# ---------------------------------------------------------------------------


class VitalSignsCreate(BaseModel):
    patient_id: int
    systolic_bp: Optional[int] = None
    diastolic_bp: Optional[int] = None
    heart_rate: Optional[int] = None
    temperature: Optional[float] = None
    respiratory_rate: Optional[int] = None
    o2_saturation: Optional[float] = None


class VitalSignsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    patient_id: int
    systolic_bp: Optional[int] = None
    diastolic_bp: Optional[int] = None
    heart_rate: Optional[int] = None
    temperature: Optional[float] = None
    respiratory_rate: Optional[int] = None
    o2_saturation: Optional[float] = None
    recorded_at: datetime
    recorded_by: Optional[int] = None


# ---------------------------------------------------------------------------
# Appointments
# ---------------------------------------------------------------------------


class AppointmentCreate(BaseModel):
    patient_id: int
    doctor_id: Optional[int] = None
    scheduled_at: datetime
    duration: int = Field(default=30, ge=5, le=480)
    notes: Optional[str] = None


class AppointmentUpdate(BaseModel):
    doctor_id: Optional[int] = None
    scheduled_at: Optional[datetime] = None
    duration: Optional[int] = Field(default=None, ge=5, le=480)
    status: Optional[AppointmentStatus] = None
    notes: Optional[str] = None


class AppointmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    patient_id: int
    doctor_id: Optional[int] = None
    scheduled_at: datetime
    duration: int
    status: AppointmentStatus
    notes: Optional[str] = None


# ---------------------------------------------------------------------------
# Diagnoses (needed for the patient summary PDF report)
# ---------------------------------------------------------------------------


class DiagnosisOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    patient_id: int
    icd10_code: str
    description: str
    pain_type: PainType
    diagnosis_date: date
    doctor_id: Optional[int] = None


class TreatmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    patient_id: int
    treatment_type: TreatmentType
    description: Optional[str] = None
    date: date
    outcome: Optional[str] = None
    cost: Optional[float] = None
    performed_by: Optional[int] = None
