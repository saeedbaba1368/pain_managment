"""Report download endpoints — thin HTTP wrapper around utils/pdf_generator.py.
Streams the PDF bytes back with a Content-Disposition attachment header."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session

from api.deps import audit, get_current_user, get_db, resolve_patient_scope
from core.i18n import Language
from models import Diagnosis, Medication, MedicationLog, PainRecord, Treatment, User
from utils.pdf_generator import (
    generate_insurance_report_pdf,
    generate_medication_history_pdf,
    generate_patient_summary_pdf,
    generate_pain_progress_report,
)

router = APIRouter(prefix="/reports", tags=["reports"])


def _pdf_response(pdf_bytes: bytes, filename: str) -> Response:
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/patients/{patient_id}/summary")
def patient_summary_report(
    patient_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    lang: Language = Query("en"),
) -> Response:
    patient = resolve_patient_scope(patient_id, db, current_user)
    diagnoses = db.query(Diagnosis).filter(Diagnosis.patient_id == patient_id).all()
    medications = db.query(Medication).filter(Medication.patient_id == patient_id).all()
    treatments = db.query(Treatment).filter(Treatment.patient_id == patient_id).all()

    pdf_bytes = generate_patient_summary_pdf(patient, diagnoses, medications, treatments, lang=lang)
    audit(db, request, current_user, action="EXPORT", table_name="patients", record_id=patient_id, details={"report": "summary"})
    return _pdf_response(pdf_bytes, f"patient-{patient_id}-summary.pdf")


@router.get("/patients/{patient_id}/pain-progress")
def pain_progress_report(
    patient_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    lang: Language = Query("en"),
) -> Response:
    patient = resolve_patient_scope(patient_id, db, current_user)
    pain_records = (
        db.query(PainRecord).filter(PainRecord.patient_id == patient_id).order_by(PainRecord.timestamp).all()
    )
    pdf_bytes = generate_pain_progress_report(patient, pain_records, lang=lang)
    audit(db, request, current_user, action="EXPORT", table_name="pain_records", record_id=patient_id, details={"report": "pain_progress"})
    return _pdf_response(pdf_bytes, f"patient-{patient_id}-pain-progress.pdf")


@router.get("/patients/{patient_id}/medication-history")
def medication_history_report(
    patient_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    lang: Language = Query("en"),
) -> Response:
    patient = resolve_patient_scope(patient_id, db, current_user)
    medications = db.query(Medication).filter(Medication.patient_id == patient_id).all()
    logs_by_medication: dict[int, list[MedicationLog]] = {}
    for m in medications:
        logs_by_medication[m.id] = db.query(MedicationLog).filter(MedicationLog.medication_id == m.id).all()

    pdf_bytes = generate_medication_history_pdf(patient, medications, logs_by_medication, lang=lang)
    audit(db, request, current_user, action="EXPORT", table_name="medications", record_id=patient_id, details={"report": "medication_history"})
    return _pdf_response(pdf_bytes, f"patient-{patient_id}-medication-history.pdf")


@router.get("/patients/{patient_id}/insurance")
def insurance_report(
    patient_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    lang: Language = Query("en"),
) -> Response:
    patient = resolve_patient_scope(patient_id, db, current_user)
    diagnoses = db.query(Diagnosis).filter(Diagnosis.patient_id == patient_id).all()
    treatments = db.query(Treatment).filter(Treatment.patient_id == patient_id).all()

    pdf_bytes = generate_insurance_report_pdf(patient, diagnoses, treatments, lang=lang)
    audit(db, request, current_user, action="EXPORT", table_name="treatments", record_id=patient_id, details={"report": "insurance"})
    return _pdf_response(pdf_bytes, f"patient-{patient_id}-insurance.pdf")
