"""Pain tracking page: clinician selects a patient, taps body-map hotspots,
sets a VAS score + pain quality, and submits a PainRecord. Below the entry
form, a chart + table show that patient's recent history.

Route: /pain-tracking (see NAV_ITEMS in layouts/sidebar.py — admin/doctor/nurse only).
"""
from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import dcc, html

from components.body_map import build_body_map_figure
from core.i18n import Language, t

PAIN_QUALITY_OPTIONS = ["burning", "stabbing", "throbbing", "aching", "sharp"]


def _quality_options(lang: Language) -> list[dict]:
    # Pain quality is a free-text clinical term today (see models/pain_record.py
    # pain_quality column) rather than an enum, so labels aren't in TRANSLATIONS —
    # keep the value in English (stored as-is) and only localize the display label.
    fa_labels = {
        "burning": "سوزش",
        "stabbing": "تیر کشیدن",
        "throbbing": "ضربان‌دار",
        "aching": "درد مبهم",
        "sharp": "تیز",
    }
    return [
        {"label": fa_labels[q] if lang == "fa" else q.capitalize(), "value": q}
        for q in PAIN_QUALITY_OPTIONS
    ]


def build_pain_tracking(lang: Language = "en") -> html.Div:
    return html.Div(
        [
            # Fires once on mount to populate the patient dropdown — same trick
            # used nowhere else yet in this codebase, documented here since it's new:
            # a 1-shot dcc.Interval avoids needing a separate "page load" signal.
            dcc.Interval(id="pain-tracking-init", interval=1, max_intervals=1),
            dcc.Store(id="selected-body-parts-store", data=[]),

            html.H4(t("nav.pain_tracking", lang), className="mb-3"),

            dbc.Row(
                [
                    dbc.Col(
                        dbc.Card(
                            dbc.CardBody(
                                [
                                    dbc.Label(t("pain.select_patient", lang)),
                                    dcc.Dropdown(id="pain-patient-select", clearable=False, className="mb-3"),
                                    dcc.Graph(
                                        id="body-map-graph",
                                        figure=build_body_map_figure(lang=lang),
                                        config={"displayModeBar": False},
                                    ),
                                    html.P(
                                        t("pain.select_locations_hint", lang),
                                        className="text-muted small mt-2 mb-1",
                                    ),
                                    html.Div(id="selected-body-parts-display", className="mb-2"),
                                ]
                            ),
                            className="shadow-sm h-100",
                        ),
                        lg=6,
                        className="mb-3",
                    ),
                    dbc.Col(
                        dbc.Card(
                            dbc.CardBody(
                                [
                                    dbc.Label(t("pain.vas_label", lang)),
                                    dcc.Slider(
                                        id="pain-vas-slider",
                                        min=0,
                                        max=10,
                                        step=1,
                                        value=5,
                                        marks={i: str(i) for i in range(0, 11)},
                                        className="mb-4",
                                    ),
                                    dbc.Label(t("pain.quality", lang)),
                                    dcc.Dropdown(
                                        id="pain-quality-select",
                                        options=_quality_options(lang),
                                        value=PAIN_QUALITY_OPTIONS[0],
                                        clearable=False,
                                        className="mb-3",
                                    ),
                                    dbc.Textarea(
                                        id="pain-notes-input",
                                        placeholder=t("pain.notes_placeholder", lang),
                                        className="mb-3",
                                    ),
                                    dbc.Button(
                                        t("pain.submit", lang),
                                        id="pain-submit-button",
                                        color="primary",
                                        className="w-100 mb-2",
                                        n_clicks=0,
                                    ),
                                    html.Div(id="pain-submit-feedback"),
                                ]
                            ),
                            className="shadow-sm h-100",
                        ),
                        lg=6,
                        className="mb-3",
                    ),
                ]
            ),

            html.H5(t("pain.recent_history", lang), className="mt-2 mb-3"),
            dbc.Row(
                [
                    dbc.Col(dcc.Graph(id="pain-history-chart"), lg=7, className="mb-3"),
                    dbc.Col(html.Div(id="pain-history-table"), lg=5, className="mb-3"),
                ]
            ),
        ]
    )
