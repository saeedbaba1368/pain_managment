"""Pain records (VAS + body map). Staff can record on behalf of any patient;
a `patient`-role user may only create/list records for their own linked
patient profile — this is the mobile self-report path (spec feature #10)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session, joinedload

from api.deps import audit, get_current_user, get_db, resolve_patient_scope
from models import BodyMapPoint, PainRecord, User, UserRole
from api.schemas import Page, PainRecordCreate, PainRecordOut

router = APIRouter(prefix="/pain-records", tags=["pain-records"])


@router.get("", response_model=Page[PainRecordOut])
def list_pain_records(
    patient_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
) -> Page[PainRecordOut]:
    resolve_patient_scope(patient_id, db, current_user)  # 404s if a patient user asks for someone else

    query = (
        db.query(PainRecord)
        .options(joinedload(PainRecord.body_map_points))
        .filter(PainRecord.patient_id == patient_id)
        .order_by(PainRecord.timestamp.desc())
    )
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    audit(db, request, current_user, action="READ", table_name="pain_records", details={"patient_id": patient_id})
    return Page(items=items, total=total, page=page, page_size=page_size)


@router.post("", response_model=PainRecordOut, status_code=status.HTTP_201_CREATED)
def create_pain_record(
    payload: PainRecordCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PainRecord:
    patient = resolve_patient_scope(payload.patient_id, db, current_user)

    if not payload.body_locations and not payload.body_map_points:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Select at least one body location")

    self_reported = current_user.role == UserRole.PATIENT
    record = PainRecord(
        patient_id=patient.id,
        vas_score=payload.vas_score,
        body_locations=payload.body_locations,
        pain_quality=payload.pain_quality,
        notes=payload.notes,
        self_reported=self_reported or payload.self_reported,
        recorded_by=current_user.id,
    )
    record.body_map_points = [
        BodyMapPoint(body_part=p.body_part, x_coord=p.x_coord, y_coord=p.y_coord, intensity=p.intensity)
        for p in payload.body_map_points
    ]
    db.add(record)
    db.commit()
    db.refresh(record)

    audit(db, request, current_user, action="CREATE", table_name="pain_records", record_id=record.id)

    # High-pain alert is fired asynchronously by callbacks/alerts in the Dash
    # app (it polls via dcc.Interval); the REST write path only persists the
    # record and audits it — see utils/alerts.py for threshold logic.
    return record


@router.get("/{record_id}", response_model=PainRecordOut)
def get_pain_record(
    record_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PainRecord:
    record = db.get(PainRecord, record_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pain record not found")
    resolve_patient_scope(record.patient_id, db, current_user)
    audit(db, request, current_user, action="READ", table_name="pain_records", record_id=record.id)
    return record
