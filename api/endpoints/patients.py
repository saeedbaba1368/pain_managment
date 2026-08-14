"""Patient CRUD + search/filter. Staff (admin/doctor/nurse) manage any
patient; a `patient`-role user may only ever read their own record via
GET /patients/{id} (enforced by resolve_patient_scope)."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from api.deps import audit, get_current_user, get_db, require_staff, resolve_patient_scope
from models import Patient, User
from api.schemas import Page, PatientCreate, PatientOut, PatientUpdate

router = APIRouter(prefix="/patients", tags=["patients"])


@router.get("", response_model=Page[PatientOut], dependencies=[Depends(require_staff)])
def list_patients(
    db: Session = Depends(get_db),
    q: Optional[str] = Query(None, description="Search by name, phone, or national code"),
    city: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
) -> Page[PatientOut]:
    """Search & filter (spec feature #11). Note: national_code and phone are
    stored encrypted at rest (EncryptedString), so free-text `q` matches
    against the plaintext name columns and city — not an encrypted-column
    LIKE, which Postgres can't do without decrypting every row first.
    """
    query = db.query(Patient)
    if q:
        like = f"%{q}%"
        query = query.filter(or_(Patient.first_name.ilike(like), Patient.last_name.ilike(like)))
    if city:
        query = query.filter(Patient.city.ilike(f"%{city}%"))

    total = query.count()
    items = query.order_by(Patient.id).offset((page - 1) * page_size).limit(page_size).all()
    return Page(items=items, total=total, page=page, page_size=page_size)


@router.post("", response_model=PatientOut, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_staff)])
def create_patient(
    payload: PatientCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Patient:
    # NOTE on this uniqueness check: national_code is stored via EncryptedString
    # (Fernet), and Fernet ciphertext is non-deterministic (random IV per call) —
    # `Patient.national_code == payload.national_code` at the SQL layer would
    # compare ciphertexts that never match, even for the same plaintext, so it
    # can't be used to enforce the `unique=True` constraint at the app level.
    # Decrypting and comparing in Python is correct but O(n); for a clinic at
    # the "1000+ patients/month" scale in the spec this is still fine. At much
    # larger scale, add a separate deterministic-hash lookup column (e.g. an
    # HMAC-SHA256 of the national code) and index that instead.
    existing = db.query(Patient).all()
    if any(p.national_code == payload.national_code for p in existing):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A patient with this national code already exists")

    patient = Patient(**payload.model_dump())
    db.add(patient)
    db.commit()
    db.refresh(patient)

    audit(db, request, current_user, action="CREATE", table_name="patients", record_id=patient.id)
    return patient


@router.get("/{patient_id}", response_model=PatientOut)
def get_patient(
    patient_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Patient:
    patient = resolve_patient_scope(patient_id, db, current_user)
    audit(db, request, current_user, action="READ", table_name="patients", record_id=patient.id)
    return patient


@router.patch("/{patient_id}", response_model=PatientOut, dependencies=[Depends(require_staff)])
def update_patient(
    patient_id: int,
    payload: PatientUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Patient:
    patient = db.get(Patient, patient_id)
    if patient is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(patient, field, value)

    db.commit()
    db.refresh(patient)
    audit(db, request, current_user, action="UPDATE", table_name="patients", record_id=patient.id)
    return patient


@router.delete("/{patient_id}", status_code=status.HTTP_200_OK, dependencies=[Depends(require_staff)])
def delete_patient(
    patient_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Deletes a patient and all dependent clinical records (cascade set at
    the DB level — see models/patient.py relationships)."""
    patient = db.get(Patient, patient_id)
    if patient is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")

    audit(db, request, current_user, action="DELETE", table_name="patients", record_id=patient.id)
    db.delete(patient)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
