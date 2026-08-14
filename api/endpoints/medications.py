"""Medications + adherence logs + side effects. Prescribing is staff-only;
patients may confirm doses taken and report side effects for their own
active medications (spec feature #10: 'medication taken confirmation')."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from api.deps import audit, get_current_user, get_db, require_prescriber, resolve_patient_scope
from models import Medication, MedicationLog, SideEffect, User
from api.schemas import (
    MedicationCreate,
    MedicationLogCreate,
    MedicationLogOut,
    MedicationOut,
    Page,
    SideEffectCreate,
    SideEffectOut,
)

router = APIRouter(prefix="/medications", tags=["medications"])


@router.get("", response_model=Page[MedicationOut])
def list_medications(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    active_only: bool = False,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
) -> Page[MedicationOut]:
    resolve_patient_scope(patient_id, db, current_user)
    query = db.query(Medication).filter(Medication.patient_id == patient_id)
    if active_only:
        query = query.filter((Medication.end_date.is_(None)))
    total = query.count()
    items = query.order_by(Medication.start_date.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return Page(items=items, total=total, page=page, page_size=page_size)


@router.post(
    "",
    response_model=MedicationOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_prescriber)],
)
def prescribe_medication(
    payload: MedicationCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Medication:
    resolve_patient_scope(payload.patient_id, db, current_user)
    medication = Medication(**payload.model_dump(), prescribed_by=current_user.id)
    db.add(medication)
    db.commit()
    db.refresh(medication)

    audit(
        db,
        request,
        current_user,
        action="CREATE",
        table_name="medications",
        record_id=medication.id,
        details={"is_opioid": medication.is_opioid},
    )
    return medication


@router.post("/{medication_id}/logs", response_model=MedicationLogOut, status_code=status.HTTP_201_CREATED)
def log_dose(
    medication_id: int,
    payload: MedicationLogCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MedicationLog:
    """Patient (or staff, for in-clinic administration) confirms a dose was
    taken or missed. Feeds the missed-dose alert (spec feature #7)."""
    medication = db.get(Medication, medication_id)
    if medication is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Medication not found")
    resolve_patient_scope(medication.patient_id, db, current_user)

    log = MedicationLog(medication_id=medication_id, **payload.model_dump())
    db.add(log)
    db.commit()
    db.refresh(log)
    audit(db, request, current_user, action="CREATE", table_name="medication_logs", record_id=log.id)
    return log


@router.post("/side-effects", response_model=SideEffectOut, status_code=status.HTTP_201_CREATED)
def report_side_effect(
    payload: SideEffectCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SideEffect:
    resolve_patient_scope(payload.patient_id, db, current_user)
    medication = db.get(Medication, payload.medication_id)
    if medication is None or medication.patient_id != payload.patient_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Medication not found for this patient")

    effect = SideEffect(**payload.model_dump())
    db.add(effect)
    db.commit()
    db.refresh(effect)
    audit(db, request, current_user, action="CREATE", table_name="side_effects", record_id=effect.id)
    return effect
