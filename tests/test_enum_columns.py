"""
Regression test for a systemic bug found when actually running
`migrations/seed_data.py` against Postgres: every `sqlalchemy.Enum(...)`
column in the models defaulted to binding the Python enum member's
`.name` (e.g. "ADMIN"), while the Postgres enum types the migration
creates only accept the lowercase `.value` labels (e.g. "admin") --
every INSERT/UPDATE on any of these columns failed with
`InvalidTextRepresentation`.

Fixed by adding `values_callable=lambda e: [x.value for x in e]` to
each column. This test inspects the column type's `.enums` directly
(what SQLAlchemy will actually send to the DB) so a future column that
forgets `values_callable` fails fast here instead of at seed/insert
time. No database connection needed.
"""
from __future__ import annotations

import pytest


@pytest.mark.parametrize(
    "module_name, model_name, column_name, expected_values",
    [
        ("models.user", "User", "role", ["admin", "doctor", "nurse", "patient"]),
        ("models.user", "User", "language_pref", ["fa", "en"]),
        ("models.patient", "Patient", "gender", ["male", "female", "other"]),
        (
            "models.patient",
            "Patient",
            "blood_type",
            ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-", "unknown"],
        ),
        ("models.diagnosis", "Diagnosis", "pain_type", ["chronic", "acute", "post_surgical", "cancer"]),
        (
            "models.treatment",
            "Treatment",
            "treatment_type",
            ["physical_therapy", "injection", "surgery", "medication"],
        ),
        (
            "models.appointment",
            "Appointment",
            "status",
            ["scheduled", "completed", "cancelled", "no_show"],
        ),
    ],
)
def test_enum_column_binds_lowercase_values_matching_postgres_enum_type(
    module_name, model_name, column_name, expected_values
):
    import importlib

    module = importlib.import_module(module_name)
    model = getattr(module, model_name)
    column = model.__table__.c[column_name]

    # This is exactly what SQLAlchemy will send as the Postgres ENUM
    # labels -- if values_callable is missing, this list is the member
    # *names* ("ADMIN", "DOCTOR", ...) instead of the values below, and
    # every insert against a real Postgres enum column fails.
    assert list(column.type.enums) == expected_values
