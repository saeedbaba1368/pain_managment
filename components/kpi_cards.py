"""Reusable KPI summary cards for the dashboard overview row."""
from __future__ import annotations

from typing import Optional

import dash_bootstrap_components as dbc
from dash import html


def build_kpi_card(
    title: str,
    value: str,
    icon: str,
    color: str = "primary",
    subtitle: Optional[str] = None,
) -> dbc.Col:
    """One KPI tile. `icon` is a Bootstrap Icons class, e.g. 'bi-people'."""
    return dbc.Col(
        dbc.Card(
            dbc.CardBody(
                [
                    html.Div(
                        className="d-flex align-items-center justify-content-between",
                        children=[
                            html.Div(
                                [
                                    html.P(title, className="text-muted mb-1 small"),
                                    html.H3(value, className="mb-0"),
                                    html.P(subtitle, className="text-muted mb-0 small") if subtitle else None,
                                ]
                            ),
                            html.I(className=f"bi {icon} fs-2 text-{color}"),
                        ],
                    )
                ]
            ),
            className=f"kpi-card border-start border-4 border-{color} shadow-sm h-100",
        ),
        xs=12,
        sm=6,
        lg=3,
        className="mb-3",
    )


def build_kpi_row(
    total_patients: int,
    avg_pain_score: float,
    active_treatments: int,
    active_alerts: int,
    lang: str = "en",
) -> dbc.Row:
    labels = {
        "en": ("Total Patients", "Avg Pain Score (30d)", "Active Treatments", "Active Alerts"),
        "fa": ("کل بیماران", "میانگین درد (۳۰ روز)", "درمان‌های فعال", "هشدارهای فعال"),
    }
    t1, t2, t3, t4 = labels.get(lang, labels["en"])

    pain_color = "success" if avg_pain_score < 4 else "warning" if avg_pain_score < 7 else "danger"
    alert_color = "success" if active_alerts == 0 else "warning" if active_alerts < 5 else "danger"

    return dbc.Row(
        [
            build_kpi_card(t1, f"{total_patients:,}", "bi-people", "primary"),
            build_kpi_card(t2, f"{avg_pain_score:.1f} / 10", "bi-clipboard2-pulse", pain_color),
            build_kpi_card(t3, f"{active_treatments:,}", "bi-heart-pulse", "info"),
            build_kpi_card(t4, f"{active_alerts:,}", "bi-exclamation-triangle", alert_color),
        ]
    )
