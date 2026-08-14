"""Main dashboard: KPI overview + trend/effectiveness/distribution/outcomes charts.
Refreshes every 60s via dcc.Interval so staff see near-real-time numbers."""
from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import dcc, html

from core.i18n import Language, t


def build_dashboard(lang: Language = "en") -> html.Div:
    return html.Div(
        [
            dcc.Interval(id="dashboard-interval", interval=60_000, n_intervals=0),
            html.H4(t("nav.dashboard", lang), className="mb-3"),
            html.Div(id="kpi-row", children=dbc.Spinner(size="sm")),
            dbc.Row(
                [
                    dbc.Col(dcc.Graph(id="pain-trend-chart"), lg=6, className="mb-3"),
                    dbc.Col(dcc.Graph(id="med-effectiveness-chart"), lg=6, className="mb-3"),
                ]
            ),
            dbc.Row(
                [
                    dbc.Col(dcc.Graph(id="distribution-pie-chart"), lg=4, className="mb-3"),
                    dbc.Col(dcc.Graph(id="age-distribution-chart"), lg=4, className="mb-3"),
                    dbc.Col(dcc.Graph(id="treatment-outcomes-chart"), lg=4, className="mb-3"),
                ]
            ),
        ]
    )
