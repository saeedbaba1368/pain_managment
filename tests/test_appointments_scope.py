"""
Regression test for the appointments IDOR fix (api/endpoints/appointments.py
list_appointments): a `patient`-role user calling GET /appointments with no
patient_id used to receive every patient's appointments. It must now always
be scoped to their own patient record.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

import pytest
from fastapi import HTTPException


@dataclass
class FakeAppointment:
    id: int
    patient_id: int
    doctor_id: int
    scheduled_at: datetime = datetime(2026, 1, 1, tzinfo=timezone.utc)
    duration: int = 30
    status: str = "scheduled"
    notes: Optional[str] = None


@dataclass
class FakePatientProfile:
    id: int


@dataclass
class FakeUser:
    id: int
    role: object
    patient_profile: Optional[FakePatientProfile] = None


class _FakeQuery:
    """Chainable stand-in for sqlalchemy.orm.Query, filtering an in-memory
    list of FakeAppointment rows. `filter()` reads the bound comparison
    value off the SQLAlchemy BinaryExpression the endpoint constructs
    (e.g. `Appointment.patient_id == 5`), same column/value a real query
    would end up filtering on -- just without a database or SQL compile."""

    def __init__(self, rows, filtered_patient_id="NOT_CALLED"):
        self._rows = rows
        self.filtered_patient_id = filtered_patient_id

    def filter(self, condition):
        column_name = condition.left.name
        value = condition.right.value
        if column_name == "patient_id":
            self.filtered_patient_id = value
        rows = [r for r in self._rows if getattr(r, column_name) == value]
        return _FakeQuery(rows, self.filtered_patient_id)

    def order_by(self, *_args):
        return self

    def count(self):
        return len(self._rows)

    def offset(self, _n):
        return self

    def limit(self, _n):
        return self

    def all(self):
        return self._rows


class FakeSession:
    def __init__(self, appointments):
        self._query = _FakeQuery(appointments)

    def query(self, _model):
        return self._query


def test_patient_role_only_ever_sees_own_appointments():
    from api.endpoints import appointments as appointments_module
    from models import UserRole

    all_appointments = [
        FakeAppointment(id=1, patient_id=5, doctor_id=1),
        FakeAppointment(id=2, patient_id=7, doctor_id=1),  # someone else's
        FakeAppointment(id=3, patient_id=5, doctor_id=2),
    ]
    db = FakeSession(all_appointments)
    patient_user = FakeUser(id=42, role=UserRole.PATIENT, patient_profile=FakePatientProfile(id=5))

    result = appointments_module.list_appointments(
        db=db, current_user=patient_user, patient_id=None, doctor_id=None, page=1, page_size=25
    )

    # Must have been forced onto the patient's own id -- not left unscoped,
    # and not trusting a client-supplied patient_id (there was none here).
    assert db._query.filtered_patient_id == 5
    assert all(item.patient_id == 5 for item in result.items)
    assert not any(item.patient_id == 7 for item in result.items)


def test_patient_role_without_profile_gets_404():
    from api.endpoints import appointments as appointments_module
    from models import UserRole

    patient_user = FakeUser(id=42, role=UserRole.PATIENT, patient_profile=None)

    with pytest.raises(HTTPException) as exc_info:
        appointments_module.list_appointments(
            db=object(), current_user=patient_user, patient_id=None, doctor_id=None, page=1, page_size=25
        )
    assert exc_info.value.status_code == 404
