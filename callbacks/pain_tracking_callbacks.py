"""
Callbacks for the pain-tracking page (layouts/pain_tracking.py).

Split into four callbacks, deliberately not combined:
  1. populate the patient dropdown once on mount
  2. toggle a body-map hotspot in/out of the pending-selection store on click
  3. re-render the figure + chip list whenever that store (or language) changes
  4. submit -> write PainRecord + BodyMapPoint rows, then refresh history

Splitting (2) from (3) avoids a callback that both reads and writes
dcc.Graph.figure from the same clickData trigger, which is the standard
Dash pattern for click-driven state.
"""
from __future__ import annotations

import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, State, html
from sqlalchemy import text

from app import app
from components.body_map import BODY_PART_COORDS, build_body_map_figure
from components.charts import patient_pain_history_chart
from core.audit import audited
from core.database import engine, session_scope
from core.i18n import t
from core.security import AccessDenied, require_role
from models import BodyMapPoint, PainRecord

import pandas as pd


# ---------------------------------------------------------------------------
# 1. Patient dropdown
# ---------------------------------------------------------------------------


@app.callback(
    Output("pain-patient-select", "options"),
    Output("pain-patient-select", "value"),
    Input("pain-tracking-init", "n_intervals"),
)
def load_patients(_n_intervals: int):
    """Names aren't encrypted (only national_code/phone/address are — see
    models/patient.py), so a plain SQL projection is safe here."""
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT id, first_name, last_name FROM patients ORDER BY last_name, first_name LIMIT 500")
        ).all()
    options = [{"label": f"{r.first_name} {r.last_name}", "value": r.id} for r in rows]
    default_value = options[0]["value"] if options else None
    return options, default_value


# ---------------------------------------------------------------------------
# 2. Click-to-toggle a hotspot
# ---------------------------------------------------------------------------


@app.callback(
    Output("selected-body-parts-store", "data", allow_duplicate=True),
    Input("body-map-graph", "clickData"),
    State("selected-body-parts-store", "data"),
    State("pain-vas-slider", "value"),
    prevent_initial_call=True,
)
def toggle_body_part(click_data: dict, selected: list[dict], vas_score: int):
    if not click_data:
        return dash.no_update

    body_part = click_data["points"][0].get("customdata")
    if body_part not in BODY_PART_COORDS:
        return dash.no_update

    selected = list(selected or [])
    existing_idx = next((i for i, p in enumerate(selected) if p["body_part"] == body_part), None)
    if existing_idx is not None:
        selected.pop(existing_idx)  # second click on the same hotspot deselects it
    else:
        selected.append({"body_part": body_part, "intensity": vas_score})
    return selected


# ---------------------------------------------------------------------------
# 3. Re-render figure + chip list from the store
# ---------------------------------------------------------------------------


@app.callback(
    Output("body-map-graph", "figure"),
    Output("selected-body-parts-display", "children"),
    Input("selected-body-parts-store", "data"),
    Input("session-lang", "data"),
)
def render_body_map(selected: list[dict], lang: str):
    lang = lang or "en"
    figure = build_body_map_figure(selected, lang=lang)

    if not selected:
        chips = html.Small(t("pain.none_selected", lang), className="text-muted")
    else:
        chips = [
            dbc.Badge(t(f"body_part.{p['body_part']}", lang), color="info", className="me-1 mb-1")
            for p in selected
        ]
    return figure, chips


# ---------------------------------------------------------------------------
# 4. Submit — writes the record, audited, role-gated
# ---------------------------------------------------------------------------


@audited("CREATE", "pain_records")
def _create_pain_record(db, *, patient_id: int, vas_score: int, quality: str, notes: str | None,
                         body_points: list[dict], recorded_by: int | None) -> PainRecord:
    record = PainRecord(
        patient_id=patient_id,
        vas_score=vas_score,
        body_locations=[p["body_part"] for p in body_points],
        pain_quality=quality,
        notes=notes or None,
        recorded_by=recorded_by,
        self_reported=False,
    )
    db.add(record)
    db.flush()
    for p in body_points:
        x, y = BODY_PART_COORDS[p["body_part"]]
        db.add(
            BodyMapPoint(
                pain_record_id=record.id,
                body_part=p["body_part"],
                x_coord=x,
                y_coord=y,
                intensity=vas_score,
            )
        )
    return record


@app.callback(
    Output("pain-submit-feedback", "children"),
    Output("selected-body-parts-store", "data", allow_duplicate=True),
    Output("pain-history-chart", "figure"),
    Output("pain-history-table", "children"),
    Input("pain-submit-button", "n_clicks"),
    Input("pain-patient-select", "value"),
    State("pain-vas-slider", "value"),
    State("pain-quality-select", "value"),
    State("pain-notes-input", "value"),
    State("selected-body-parts-store", "data"),
    State("session-lang", "data"),
    prevent_initial_call=True,
)
def handle_submit_or_patient_change(n_clicks: int, patient_id, vas_score, quality, notes,
                                     selected: list[dict], lang: str):
    """Fires on submit-click OR on patient-selection change, so switching
    patients always shows that patient's own history, and a genuine submit
    (triggered_id == submit button) also writes the record first."""
    lang = lang or "en"
    triggered_id = dash.ctx.triggered_id
    feedback = ""
    cleared_selection = dash.no_update

    if triggered_id == "pain-submit-button":
        if not patient_id:
            feedback = dbc.Alert(t("pain.record_error_no_patient", lang), color="danger")
        elif not selected:
            feedback = dbc.Alert(t("pain.record_error_no_location", lang), color="danger")
        else:
            try:
                from flask_login import current_user

                _require_clinician()
                with session_scope() as db:
                    _create_pain_record(
                        db,
                        patient_id=patient_id,
                        vas_score=vas_score,
                        quality=quality,
                        notes=notes,
                        body_points=selected,
                        recorded_by=current_user.id if current_user.is_authenticated else None,
                    )
                feedback = dbc.Alert(t("pain.record_success", lang), color="success")
                cleared_selection = []
            except AccessDenied as exc:
                feedback = dbc.Alert(str(exc), color="danger")

    history_fig, history_table = _load_history(patient_id, lang)
    return feedback, cleared_selection, history_fig, history_table


@require_role("admin", "doctor", "nurse")
def _require_clinician() -> None:
    """Thin wrapper so require_role's normal decorator usage (see
    core/security.py) can gate this write path without decorating the
    Dash callback itself (callbacks need a stable signature for Dash).
    require_role reads flask_login.current_user internally."""
    return None


def _load_history(patient_id, lang: str):
    if not patient_id:
        return patient_pain_history_chart(pd.DataFrame(columns=["timestamp", "vas_score"])), html.Small(
            t("pain.no_history", lang), className="text-muted"
        )

    query = text(
        "SELECT timestamp, vas_score, pain_quality, body_locations FROM pain_records "
        "WHERE patient_id = :pid ORDER BY timestamp DESC LIMIT 20"
    )
    df = pd.read_sql(query, engine, params={"pid": patient_id})

    fig = patient_pain_history_chart(df[["timestamp", "vas_score"]] if not df.empty else df)

    if df.empty:
        table = html.Small(t("pain.no_history", lang), className="text-muted")
    else:
        rows = [
            html.Tr(
                [
                    html.Td(row.timestamp.strftime("%Y-%m-%d %H:%M")),
                    html.Td(dbc.Badge(str(row.vas_score), color="secondary")),
                    html.Td(row.pain_quality or "-"),
                    html.Td(", ".join(t(f"body_part.{p}", lang) for p in (row.body_locations or []))),
                ]
            )
            for row in df.itertuples()
        ]
        table = dbc.Table(
            [html.Tbody(rows)],
            bordered=False,
            hover=True,
            size="sm",
            className="mb-0",
        )
    return fig, table
