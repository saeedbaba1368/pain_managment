"""
Dashboard callbacks: pulls KPI numbers and chart data from Postgres on a
60s interval (see dcc.Interval in layouts/dashboard.py) and on language change.

Raw SQL (via pandas.read_sql) is used here instead of the ORM for the
aggregate queries — they're read-only reporting queries over non-PII
columns, and SQL aggregation is both faster and clearer than pulling rows
into Python. PII columns (national_code, phone, address, emergency_contact)
are encrypted at rest and are never touched by these queries.
"""
from __future__ import annotations

from datetime import date

import pandas as pd
from dash import Input, Output
from sqlalchemy import text

from app import app
from components.charts import (
    age_distribution_bar,
    medication_effectiveness_chart,
    pain_trend_chart,
    patient_distribution_pie,
    treatment_outcomes_chart,
)
from components.kpi_cards import build_kpi_row
from config import settings
from core.database import engine

AGE_BUCKETS = [(0, 17), (18, 34), (35, 49), (50, 64), (65, 120)]
AGE_LABELS = ["0-17", "18-34", "35-49", "50-64", "65+"]


def _bucket_age(age: int) -> str:
    for (lo, hi), label in zip(AGE_BUCKETS, AGE_LABELS):
        if lo <= age <= hi:
            return label
    return AGE_LABELS[-1]


def _fetch_kpis() -> dict:
    with engine.connect() as conn:
        total_patients = conn.execute(text("SELECT COUNT(*) FROM patients")).scalar() or 0

        avg_pain = conn.execute(
            text(
                "SELECT AVG(vas_score) FROM pain_records "
                "WHERE timestamp >= NOW() - INTERVAL '30 days'"
            )
        ).scalar()
        avg_pain = float(avg_pain) if avg_pain is not None else 0.0

        active_treatments = conn.execute(
            text("SELECT COUNT(*) FROM medications WHERE end_date IS NULL OR end_date >= CURRENT_DATE")
        ).scalar() or 0

        high_pain_alerts = conn.execute(
            text(
                "SELECT COUNT(*) FROM pain_records "
                "WHERE vas_score >= :threshold AND timestamp >= NOW() - INTERVAL '24 hours'"
            ),
            {"threshold": settings.HIGH_PAIN_VAS_THRESHOLD},
        ).scalar() or 0

        missed_dose_alerts = conn.execute(
            text(
                "SELECT COUNT(*) FROM medication_logs "
                "WHERE missed = TRUE AND taken_at >= NOW() - INTERVAL '7 days'"
            )
        ).scalar() or 0

        upcoming_appt_alerts = conn.execute(
            text(
                "SELECT COUNT(*) FROM appointments "
                "WHERE status = 'scheduled' AND scheduled_at BETWEEN NOW() AND NOW() + INTERVAL '24 hours'"
            )
        ).scalar() or 0

        opioid_overuse_alerts = conn.execute(
            text(
                "SELECT COUNT(*) FROM medications "
                "WHERE is_opioid = TRUE AND (end_date IS NULL OR end_date >= CURRENT_DATE) "
                "AND start_date <= CURRENT_DATE - (:days || ' days')::interval"
            ),
            {"days": settings.OPIOID_ALERT_DAYS_WINDOW},
        ).scalar() or 0

    active_alerts = high_pain_alerts + missed_dose_alerts + upcoming_appt_alerts + opioid_overuse_alerts

    return {
        "total_patients": total_patients,
        "avg_pain_score": avg_pain,
        "active_treatments": active_treatments,
        "active_alerts": active_alerts,
    }


def _fetch_pain_trend() -> pd.DataFrame:
    query = text(
        "SELECT DATE(timestamp) AS date, AVG(vas_score) AS avg_vas "
        "FROM pain_records WHERE timestamp >= NOW() - INTERVAL '90 days' "
        "GROUP BY DATE(timestamp) ORDER BY date"
    )
    return pd.read_sql(query, engine)


def _fetch_medication_effectiveness() -> pd.DataFrame:
    """For each of the 5 most-prescribed drugs: avg VAS in the 14 days before
    the patient started it vs. 14-42 days after starting it."""
    query = text(
        """
        WITH top_drugs AS (
            SELECT drug_name FROM medications
            GROUP BY drug_name ORDER BY COUNT(*) DESC LIMIT 5
        ),
        med_windows AS (
            SELECT m.id AS medication_id, m.patient_id, m.drug_name, m.start_date
            FROM medications m
            JOIN top_drugs td ON td.drug_name = m.drug_name
        )
        SELECT
            mw.drug_name,
            AVG(pr.vas_score) FILTER (
                WHERE pr.timestamp::date BETWEEN mw.start_date - INTERVAL '14 days' AND mw.start_date
            ) AS avg_before,
            AVG(pr.vas_score) FILTER (
                WHERE pr.timestamp::date BETWEEN mw.start_date + INTERVAL '14 days'
                    AND mw.start_date + INTERVAL '42 days'
            ) AS avg_after
        FROM med_windows mw
        JOIN pain_records pr ON pr.patient_id = mw.patient_id
        GROUP BY mw.drug_name
        HAVING AVG(pr.vas_score) FILTER (
            WHERE pr.timestamp::date BETWEEN mw.start_date - INTERVAL '14 days' AND mw.start_date
        ) IS NOT NULL
        """
    )
    df = pd.read_sql(query, engine)
    return df.dropna(subset=["avg_before", "avg_after"])


def _fetch_pain_type_distribution() -> pd.DataFrame:
    query = text(
        "SELECT pain_type, COUNT(DISTINCT patient_id) AS count "
        "FROM diagnoses GROUP BY pain_type ORDER BY count DESC"
    )
    return pd.read_sql(query, engine)


def _fetch_age_distribution() -> pd.DataFrame:
    query = text("SELECT birth_date FROM patients")
    df = pd.read_sql(query, engine)
    if df.empty:
        return pd.DataFrame(columns=["age_group", "count"])
    today = date.today()
    df["age"] = df["birth_date"].apply(
        lambda bd: today.year - bd.year - ((today.month, today.day) < (bd.month, bd.day))
    )
    df["age_group"] = df["age"].apply(_bucket_age)
    counts = df["age_group"].value_counts().reindex(AGE_LABELS, fill_value=0).reset_index()
    counts.columns = ["age_group", "count"]
    return counts


def _fetch_treatment_outcomes() -> pd.DataFrame:
    query = text(
        "SELECT treatment_type, COALESCE(outcome, 'unknown') AS outcome, COUNT(*) AS count "
        "FROM treatments GROUP BY treatment_type, outcome"
    )
    return pd.read_sql(query, engine)


@app.callback(
    Output("kpi-row", "children"),
    Output("pain-trend-chart", "figure"),
    Output("med-effectiveness-chart", "figure"),
    Output("distribution-pie-chart", "figure"),
    Output("age-distribution-chart", "figure"),
    Output("treatment-outcomes-chart", "figure"),
    Input("dashboard-interval", "n_intervals"),
    Input("session-lang", "data"),
)
def update_dashboard(_n_intervals: int, lang: str):
    lang = lang or settings.DEFAULT_LANGUAGE

    kpis = _fetch_kpis()
    kpi_row = build_kpi_row(
        total_patients=kpis["total_patients"],
        avg_pain_score=kpis["avg_pain_score"],
        active_treatments=kpis["active_treatments"],
        active_alerts=kpis["active_alerts"],
        lang=lang,
    )

    pain_trend_fig = pain_trend_chart(_fetch_pain_trend())
    effectiveness_fig = medication_effectiveness_chart(_fetch_medication_effectiveness())
    distribution_fig = patient_distribution_pie(_fetch_pain_type_distribution())
    age_fig = age_distribution_bar(_fetch_age_distribution())
    outcomes_fig = treatment_outcomes_chart(_fetch_treatment_outcomes())

    return kpi_row, pain_trend_fig, effectiveness_fig, distribution_fig, age_fig, outcomes_fig
