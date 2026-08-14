"""Appointment scheduling (spec feature #8): book/edit/cancel, status tracking."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from api.deps import audit, get_current_user, get_db, require_staff, resolve_patient_scope
from models import Appointment, User, UserRole
from api.schemas import AppointmentCreate, AppointmentOut, AppointmentUpdate, Page

router = APIRouter(prefix="/appointments", tags=["appointments"])


@router.get("", response_model=Page[AppointmentOut])
def list_appointments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    patient_id: int | None = None,
    doctor_id: int | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
) -> Page[AppointmentOut]:
    # A `patient`-role user must never see appointments beyond their own --
    # without this, omitting patient_id (or passing only doctor_id) returned
    # every patient's appointments to anyone with a valid token (IDOR).
    if current_user.role == UserRole.PATIENT:
        own_patient = current_user.patient_profile
        if own_patient is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient profile not found")
        patient_id = own_patient.id
    elif patient_id is not None:
        resolve_patient_scope(patient_id, db, current_user)

    query = db.query(Appointment)
    if patient_id is not None:
        query = query.filter(Appointment.patient_id == patient_id)
    if doctor_id is not None:
        query = query.filter(Appointment.doctor_id == doctor_id)
    query = query.order_by(Appointment.scheduled_at)

    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return Page(items=items, total=total, page=page, page_size=page_size)


@router.post("", response_model=AppointmentOut, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_staff)])
def book_appointment(
    payload: AppointmentCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Appointment:
    resolve_patient_scope(payload.patient_id, db, current_user)
    appt = Appointment(**payload.model_dump())
    db.add(appt)
    db.commit()
    db.refresh(appt)
    audit(db, request, current_user, action="CREATE", table_name="appointments", record_id=appt.id)
    return appt


@router.patch("/{appointment_id}", response_model=AppointmentOut, dependencies=[Depends(require_staff)])
def update_appointment(
    appointment_id: int,
    payload: AppointmentUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Appointment:
    appt = db.get(Appointment, appointment_id)
    if appt is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(appt, field, value)

    db.commit()
    db.refresh(appt)
    audit(db, request, current_user, action="UPDATE", table_name="appointments", record_id=appt.id)
    return appt
