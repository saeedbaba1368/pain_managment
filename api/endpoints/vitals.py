"""Vital signs. Recorded by nursing/clinical staff at point of care."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from api.deps import audit, get_current_user, get_db, require_staff, resolve_patient_scope
from models import User, VitalSigns
from api.schemas import Page, VitalSignsCreate, VitalSignsOut

router = APIRouter(prefix="/vitals", tags=["vitals"])


@router.get("", response_model=Page[VitalSignsOut])
def list_vitals(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
) -> Page[VitalSignsOut]:
    resolve_patient_scope(patient_id, db, current_user)
    query = db.query(VitalSigns).filter(VitalSigns.patient_id == patient_id).order_by(VitalSigns.recorded_at.desc())
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return Page(items=items, total=total, page=page, page_size=page_size)


@router.post("", response_model=VitalSignsOut, status_code=201, dependencies=[Depends(require_staff)])
def record_vitals(
    payload: VitalSignsCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> VitalSigns:
    resolve_patient_scope(payload.patient_id, db, current_user)
    vitals = VitalSigns(**payload.model_dump(), recorded_by=current_user.id)
    db.add(vitals)
    db.commit()
    db.refresh(vitals)
    audit(db, request, current_user, action="CREATE", table_name="vital_signs", record_id=vitals.id)
    return vitals
