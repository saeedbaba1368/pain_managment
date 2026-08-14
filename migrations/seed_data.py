"""
Seed the database with fake data for local development and demos.

Usage:
    python -m migrations.seed_data              # seeds ~50 patients
    python -m migrations.seed_data --patients 200

Never run against a production database — this truncates clinical tables first.
"""
from __future__ import annotations

import argparse
import random
import secrets
from datetime import date, datetime, timedelta

from faker import Faker
from sqlalchemy import text

from core.database import session_scope, engine
from core.security import hash_password
from models import (
    Appointment,
    AppointmentStatus,
    BloodType,
    BodyMapPoint,
    Diagnosis,
    Gender,
    LanguagePref,
    Medication,
    MedicationLog,
    PainRecord,
    PainType,
    Patient,
    SideEffect,
    Treatment,
    TreatmentType,
    User,
    UserRole,
    VitalSigns,
)

fake = Faker()

IRANIAN_CITIES = ["Tehran", "Mashhad", "Isfahan", "Shiraz", "Tabriz", "Karaj", "Rasht", "Ahvaz"]
CITY_COORDS = {
    "Tehran": (35.6892, 51.3890),
    "Mashhad": (36.2605, 59.6168),
    "Isfahan": (32.6546, 51.6680),
    "Shiraz": (29.5918, 52.5837),
    "Tabriz": (38.0800, 46.2919),
    "Karaj": (35.8400, 50.9391),
    "Rasht": (37.2809, 49.5832),
    "Ahvaz": (31.3183, 48.6706),
}
BODY_PARTS = ["neck", "lower_back", "left_shoulder", "right_shoulder", "left_knee", "right_knee", "hip"]
OPIOID_DRUGS = ["Oxycodone", "Morphine", "Tramadol", "Fentanyl Patch"]
NON_OPIOID_DRUGS = ["Ibuprofen", "Acetaminophen", "Gabapentin", "Naproxen", "Duloxetine"]
ICD10_PAIN_CODES = ["M54.5", "M25.50", "G89.4", "M79.7", "R52"]


def truncate_all(db) -> None:
    """Wipe clinical + user tables (dev/demo only).

    Table names below are a fixed, hardcoded tuple (never user input), and
    SQLAlchemy 2.x requires raw SQL to be wrapped in text() to be executable
    via Session.execute() -- a bare f-string raises ObjectNotExecutableError.
    """
    for table in (
        "audit_logs", "appointments", "treatments", "side_effects", "medication_logs",
        "medications", "body_map_points", "pain_records", "diagnoses", "patients", "users",
    ):
        db.execute(text(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE"))  # nosec - dev seed only, fixed table list


def _generate_dev_password() -> str:
    """A fresh random password per seed run -- never a fixed/predictable
    value, even for local dev/demo data (see review checklist item D)."""
    return secrets.token_urlsafe(12)


def create_staff_users(db) -> tuple[list[User], list[User]]:
    """Create one admin, several doctors and nurses. Every seeded account
    gets its own randomly generated password, printed once below -- there
    is no shared, predictable default password for any role."""
    admin_password = _generate_dev_password()
    admin = User(
        username="admin",
        password_hash=hash_password(admin_password),
        full_name="System Administrator",
        role=UserRole.ADMIN,
        email="admin@painclinic.example",
        language_pref=LanguagePref.EN,
    )
    doctor_creds = [(f"dr.{fake.unique.user_name()}", _generate_dev_password()) for _ in range(5)]
    doctors = [
        User(
            username=username,
            password_hash=hash_password(password),
            full_name=f"Dr. {fake.name()}",
            role=UserRole.DOCTOR,
            email=fake.unique.email(),
            language_pref=LanguagePref.EN,
        )
        for username, password in doctor_creds
    ]
    nurse_creds = [(f"nurse.{fake.unique.user_name()}", _generate_dev_password()) for _ in range(8)]
    nurses = [
        User(
            username=username,
            password_hash=hash_password(password),
            full_name=fake.name(),
            role=UserRole.NURSE,
            email=fake.unique.email(),
            language_pref=LanguagePref.EN,
        )
        for username, password in nurse_creds
    ]
    db.add(admin)
    db.add_all(doctors)
    db.add_all(nurses)
    db.flush()

    print("\nSeeded staff credentials (dev/demo only -- shown once, not stored anywhere):")
    print(f"  admin            | {admin.username:<24} | {admin_password}")
    for user, (username, password) in zip(doctors, doctor_creds):
        print(f"  doctor           | {username:<24} | {password}")
    for user, (username, password) in zip(nurses, nurse_creds):
        print(f"  nurse            | {username:<24} | {password}")
    print()

    return doctors, nurses


def create_patient(db, doctors: list[User]) -> Patient:
    city = random.choice(IRANIAN_CITIES)
    lat, lon = CITY_COORDS[city]
    gender = random.choice(list(Gender))
    first = fake.first_name_male() if gender == Gender.MALE else fake.first_name_female()

    patient_user = User(
        username=f"patient.{fake.unique.user_name()}",
        password_hash=hash_password(_generate_dev_password()),
        full_name=f"{first} {fake.last_name()}",
        role=UserRole.PATIENT,
        email=fake.unique.email(),
        language_pref=LanguagePref.FA,
    )
    db.add(patient_user)
    db.flush()

    patient = Patient(
        user_id=patient_user.id,
        national_code=fake.unique.numerify("##########"),
        first_name=first,
        last_name=patient_user.full_name.split(" ")[-1],
        birth_date=fake.date_of_birth(minimum_age=18, maximum_age=90),
        gender=gender,
        phone=fake.numerify("09#########"),
        address=fake.address(),
        city=city,
        latitude=lat + random.uniform(-0.05, 0.05),
        longitude=lon + random.uniform(-0.05, 0.05),
        emergency_contact=fake.phone_number(),
        blood_type=random.choice(list(BloodType)),
    )
    db.add(patient)
    db.flush()

    # diagnosis
    pain_type = random.choice(list(PainType))
    db.add(
        Diagnosis(
            patient_id=patient.id,
            icd10_code=random.choice(ICD10_PAIN_CODES),
            description=fake.sentence(nb_words=8),
            pain_type=pain_type,
            diagnosis_date=fake.date_between(start_date="-2y", end_date="today"),
            doctor_id=random.choice(doctors).id,
        )
    )

    # pain records with body map points (history of 5-15 entries)
    for _ in range(random.randint(5, 15)):
        vas = random.randint(0, 10)
        ts = fake.date_time_between(start_date="-6M", end_date="now")
        record = PainRecord(
            patient_id=patient.id,
            vas_score=vas,
            body_locations=random.sample(BODY_PARTS, k=random.randint(1, 3)),
            pain_quality=random.choice(["burning", "stabbing", "throbbing", "aching", "sharp"]),
            timestamp=ts,
            self_reported=random.random() < 0.6,
        )
        db.add(record)
        db.flush()
        for part in record.body_locations:
            db.add(
                BodyMapPoint(
                    pain_record_id=record.id,
                    body_part=part,
                    x_coord=round(random.uniform(0.1, 0.9), 3),
                    y_coord=round(random.uniform(0.1, 0.9), 3),
                    intensity=vas,
                )
            )

    # medications (mix of opioid / non-opioid)
    for _ in range(random.randint(1, 4)):
        is_opioid = random.random() < 0.25
        drug = random.choice(OPIOID_DRUGS if is_opioid else NON_OPIOID_DRUGS)
        start = fake.date_between(start_date="-1y", end_date="-1M")
        med = Medication(
            patient_id=patient.id,
            drug_name=drug,
            dosage=f"{random.choice([5, 10, 20, 50])}mg",
            frequency=random.choice(["every 8 hours", "once daily", "twice daily", "as needed"]),
            route=random.choice(["oral", "topical", "IV"]),
            is_opioid=is_opioid,
            start_date=start,
            end_date=None if random.random() < 0.7 else start + timedelta(days=random.randint(30, 180)),
            prescribed_by=random.choice(doctors).id,
        )
        db.add(med)
        db.flush()
        for _ in range(random.randint(3, 10)):
            taken = random.random() < 0.85
            db.add(
                MedicationLog(
                    medication_id=med.id,
                    taken_at=fake.date_time_between(start_date=start, end_date="now"),
                    taken=taken,
                    missed=not taken,
                )
            )
        if random.random() < 0.3:
            db.add(
                SideEffect(
                    medication_id=med.id,
                    patient_id=patient.id,
                    effect_description=random.choice(["nausea", "drowsiness", "dizziness", "dry mouth"]),
                    severity=random.choice(["mild", "moderate", "severe"]),
                )
            )

    # vitals
    for _ in range(random.randint(2, 6)):
        db.add(
            VitalSigns(
                patient_id=patient.id,
                systolic_bp=random.randint(100, 150),
                diastolic_bp=random.randint(60, 95),
                heart_rate=random.randint(55, 100),
                temperature=round(random.uniform(36.1, 37.8), 1),
                respiratory_rate=random.randint(12, 20),
                o2_saturation=round(random.uniform(94.0, 100.0), 1),
                recorded_at=fake.date_time_between(start_date="-6M", end_date="now"),
                recorded_by=random.choice(doctors).id,
            )
        )

    # treatments
    for _ in range(random.randint(0, 3)):
        db.add(
            Treatment(
                patient_id=patient.id,
                treatment_type=random.choice(list(TreatmentType)),
                description=fake.sentence(nb_words=6),
                date=fake.date_between(start_date="-1y", end_date="today"),
                outcome=random.choice(["improved", "no change", "worsened", "resolved"]),
                cost=round(random.uniform(50, 2000), 2),
                performed_by=random.choice(doctors).id,
            )
        )

    # appointments (past + upcoming)
    for _ in range(random.randint(1, 5)):
        scheduled = fake.date_time_between(start_date="-3M", end_date="+2M")
        status = (
            random.choice([AppointmentStatus.COMPLETED, AppointmentStatus.NO_SHOW, AppointmentStatus.CANCELLED])
            if scheduled < datetime.now()
            else AppointmentStatus.SCHEDULED
        )
        db.add(
            Appointment(
                patient_id=patient.id,
                doctor_id=random.choice(doctors).id,
                scheduled_at=scheduled,
                duration=random.choice([15, 30, 45, 60]),
                status=status,
                notes=fake.sentence(nb_words=5) if random.random() < 0.5 else None,
            )
        )

    return patient


def main(num_patients: int, truncate: bool) -> None:
    with session_scope() as db:
        if truncate:
            truncate_all(db)
        doctors, _nurses = create_staff_users(db)
        for i in range(num_patients):
            create_patient(db, doctors)
            if (i + 1) % 25 == 0:
                print(f"  seeded {i + 1}/{num_patients} patients...")
    print(f"Done. Seeded {num_patients} patients.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed fake data into the pain dashboard DB.")
    parser.add_argument("--patients", type=int, default=50, help="Number of patients to generate")
    parser.add_argument(
        "--no-truncate", action="store_true", help="Skip truncating existing data before seeding"
    )
    args = parser.parse_args()
    main(num_patients=args.patients, truncate=not args.no_truncate)
