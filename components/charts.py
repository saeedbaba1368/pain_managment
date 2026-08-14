"""
Plotly figure builders. Each function takes a pandas DataFrame (already
queried from the DB by the caller) and returns a go.Figure — keeps chart
styling separate from data access, and makes these independently testable.
"""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

CLINIC_COLORWAY = ["#2c6e9e", "#4caf90", "#e2a83f", "#c9534b", "#8e6cae", "#4a4a4a"]

_LAYOUT_DEFAULTS = dict(
    margin=dict(l=40, r=20, t=40, b=40),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    colorway=CLINIC_COLORWAY,
    font=dict(size=12),
)


def _empty_figure(message: str) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(text=message, showarrow=False, font=dict(size=14, color="gray"))
    fig.update_layout(**_LAYOUT_DEFAULTS, xaxis={"visible": False}, yaxis={"visible": False})
    return fig


def pain_trend_chart(daily_avg_df: pd.DataFrame, title: str = "Average Pain Score Over Time") -> go.Figure:
    """daily_avg_df columns: ['date', 'avg_vas']"""
    if daily_avg_df.empty:
        return _empty_figure("No pain records yet")

    fig = px.line(daily_avg_df, x="date", y="avg_vas", markers=True, title=title)
    fig.update_traces(line_color=CLINIC_COLORWAY[0])
    fig.add_hrect(y0=8, y1=10, fillcolor="red", opacity=0.06, line_width=0)
    fig.update_yaxes(range=[0, 10], title="VAS score")
    fig.update_xaxes(title=None)
    fig.update_layout(**_LAYOUT_DEFAULTS)
    return fig


def medication_effectiveness_chart(
    effectiveness_df: pd.DataFrame, title: str = "Medication Effectiveness (Avg Pain: Before vs After)"
) -> go.Figure:
    """effectiveness_df columns: ['drug_name', 'avg_before', 'avg_after']"""
    if effectiveness_df.empty:
        return _empty_figure("Not enough data yet")

    fig = go.Figure()
    fig.add_bar(name="Before", x=effectiveness_df["drug_name"], y=effectiveness_df["avg_before"])
    fig.add_bar(name="After", x=effectiveness_df["drug_name"], y=effectiveness_df["avg_after"])
    fig.update_layout(barmode="group", title=title, yaxis_title="Avg VAS score", **_LAYOUT_DEFAULTS)
    return fig


def patient_distribution_pie(pain_type_counts: pd.DataFrame, title: str = "Patients by Pain Type") -> go.Figure:
    """pain_type_counts columns: ['pain_type', 'count']"""
    if pain_type_counts.empty:
        return _empty_figure("No diagnoses yet")

    fig = px.pie(pain_type_counts, names="pain_type", values="count", hole=0.4, title=title)
    fig.update_layout(**_LAYOUT_DEFAULTS)
    return fig


def age_distribution_bar(age_group_counts: pd.DataFrame, title: str = "Patients by Age Group") -> go.Figure:
    """age_group_counts columns: ['age_group', 'count'], age_group pre-sorted."""
    if age_group_counts.empty:
        return _empty_figure("No patients yet")

    fig = px.bar(age_group_counts, x="age_group", y="count", title=title)
    fig.update_layout(**_LAYOUT_DEFAULTS, xaxis_title=None, yaxis_title="Patients")
    return fig


def patient_pain_history_chart(
    records_df: pd.DataFrame, title: str = "Pain Score History"
) -> go.Figure:
    """records_df columns: ['timestamp', 'vas_score']. One patient's own
    VAS trend, most-recent-first input is fine — sorted here for display."""
    if records_df.empty:
        return _empty_figure("No pain records yet")

    df = records_df.sort_values("timestamp")
    fig = px.line(df, x="timestamp", y="vas_score", markers=True, title=title)
    fig.update_traces(line_color=CLINIC_COLORWAY[2])
    fig.add_hrect(y0=8, y1=10, fillcolor="red", opacity=0.06, line_width=0)
    fig.update_yaxes(range=[0, 10], title="VAS score")
    fig.update_xaxes(title=None)
    fig.update_layout(**_LAYOUT_DEFAULTS)
    return fig


def treatment_outcomes_chart(outcomes_df: pd.DataFrame, title: str = "Treatment Outcomes by Type") -> go.Figure:
    """outcomes_df columns: ['treatment_type', 'outcome', 'count']"""
    if outcomes_df.empty:
        return _empty_figure("No treatments recorded yet")

    fig = px.bar(
        outcomes_df,
        x="treatment_type",
        y="count",
        color="outcome",
        barmode="stack",
        title=title,
    )
    fig.update_layout(**_LAYOUT_DEFAULTS, xaxis_title=None, yaxis_title="Treatments")
    return fig
