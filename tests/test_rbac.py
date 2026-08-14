"""
RBAC / access-scoping tests using lightweight fakes instead of a real
database -- these exercise the exact decision logic (who can see whose
records) without needing Postgres running.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import pytest
from fastapi import HTTPException


@dataclass
class FakeUser:
    id: int
    role: object  # UserRole


@dataclass
class FakePatient:
    id: int
    user_id: Optional[int]


class FakeSession:
    """Minimal stand-in for sqlalchemy.orm.Session.get()."""

    def __init__(self, patients: dict[int, FakePatient]):
        self._patients = patients

    def get(self, model, pk):
        return self._patients.get(pk)


def test_resolve_patient_scope_allows_staff_to_view_any_patient():
    from api.deps import resolve_patient_scope
    from models import UserRole

    patient = FakePatient(id=5, user_id=99)
    db = FakeSession({5: patient})
    doctor = FakeUser(id=1, role=UserRole.DOCTOR)

    result = resolve_patient_scope(5, db, doctor)
    assert result is patient


def test_resolve_patient_scope_allows_patient_to_view_own_record():
    from api.deps import resolve_patient_scope
    from models import UserRole

    patient_record = FakePatient(id=5, user_id=42)
    db = FakeSession({5: patient_record})
    patient_user = FakeUser(id=42, role=UserRole.PATIENT)

    result = resolve_patient_scope(5, db, patient_user)
    assert result is patient_record


def test_resolve_patient_scope_blocks_patient_from_viewing_others():
    """The core IDOR guard: a patient-role user must never be able to
    pull another patient's record by guessing/incrementing an ID."""
    from api.deps import resolve_patient_scope
    from models import UserRole

    someone_elses_record = FakePatient(id=5, user_id=99)
    db = FakeSession({5: someone_elses_record})
    patient_user = FakeUser(id=42, role=UserRole.PATIENT)

    with pytest.raises(HTTPException) as exc_info:
        resolve_patient_scope(5, db, patient_user)
    # 404, not 403 -- deliberately doesn't confirm the record exists.
    assert exc_info.value.status_code == 404


def test_resolve_patient_scope_404s_on_missing_patient():
    from api.deps import resolve_patient_scope
    from models import UserRole

    db = FakeSession({})
    staff = FakeUser(id=1, role=UserRole.NURSE)

    with pytest.raises(HTTPException) as exc_info:
        resolve_patient_scope(999, db, staff)
    assert exc_info.value.status_code == 404


def test_require_roles_allows_permitted_role():
    from api.deps import require_roles
    from models import UserRole

    dependency = require_roles(UserRole.ADMIN, UserRole.DOCTOR)
    admin = FakeUser(id=1, role=UserRole.ADMIN)
    assert dependency(current_user=admin) is admin


def test_require_roles_blocks_unpermitted_role():
    from api.deps import require_roles
    from models import UserRole

    dependency = require_roles(UserRole.ADMIN, UserRole.DOCTOR)
    nurse = FakeUser(id=1, role=UserRole.NURSE)

    with pytest.raises(HTTPException) as exc_info:
        dependency(current_user=nurse)
    assert exc_info.value.status_code == 403
