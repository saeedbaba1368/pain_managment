"""
Interactive body pain map, rendered as a Plotly figure so clicks are captured
via clickData (Dash's built-in event, no custom JS needed) and intensity is
driven by the same color scale as the rest of the dashboard.

The silhouette is a deliberately simple schematic (head/torso/limb shapes),
not a traced medical illustration — it exists to give the hotspot markers a
recognizable body outline to click on. Hotspot coordinates are in the same
normalized 0-1 space as PainRecord.body_locations / BodyMapPoint.x_coord,y_coord
(see models/pain_record.py), and the body-part keys match seed_data.BODY_PARTS
exactly so seeded history renders without translation.

Orientation note: this is an anterior (facing-the-viewer) view. Anatomical
"left"/"right" follow the patient's own left/right, which is mirrored from
the viewer's perspective — the standard convention on clinical body charts.
lower_back has no anterior landmark, so it's placed with a dashed marker
near the flank as a posterior-reference indicator rather than a literal
front-view location.
"""
from __future__ import annotations

from typing import Optional, TypedDict

import plotly.graph_objects as go

from core.i18n import Language, t

# ---------------------------------------------------------------------------
# Hotspot geometry — keys must match seed_data.BODY_PARTS / BodyMapPoint.body_part
# ---------------------------------------------------------------------------

BODY_PART_COORDS: dict[str, tuple[float, float]] = {
    "neck": (0.50, 0.90),
    "right_shoulder": (0.38, 0.82),  # patient's right = viewer's left
    "left_shoulder": (0.62, 0.82),
    "lower_back": (0.50, 0.60),  # posterior-reference indicator, see module docstring
    "hip": (0.50, 0.50),
    "right_knee": (0.38, 0.18),
    "left_knee": (0.62, 0.18),
}

_SILHOUETTE_LINE = dict(color="#b5c0c9", width=2)
_SILHOUETTE_FILL = "rgba(181, 192, 201, 0.15)"

_INTENSITY_SCALE = [
    (0, "#4caf90"),  # 0-3 mild — clinic accent green
    (4, "#e2a83f"),  # 4-6 moderate — amber
    (7, "#c9534b"),  # 7-10 severe — red
]


def _intensity_color(intensity: int) -> str:
    color = _INTENSITY_SCALE[0][1]
    for threshold, hex_color in _INTENSITY_SCALE:
        if intensity >= threshold:
            color = hex_color
    return color


def _silhouette_shapes() -> list[dict]:
    """Head/torso/limb outline shapes, drawn in the same 0-1 coordinate
    space as the hotspots so everything lines up regardless of figure size."""
    return [
        # head
        dict(
            type="circle", x0=0.44, y0=0.86, x1=0.56, y1=0.98,
            line=_SILHOUETTE_LINE, fillcolor=_SILHOUETTE_FILL,
        ),
        # torso
        dict(
            type="rect", x0=0.35, y0=0.45, x1=0.65, y1=0.85,
            line=_SILHOUETTE_LINE, fillcolor=_SILHOUETTE_FILL,
        ),
        # arms
        dict(type="line", x0=0.35, y0=0.82, x1=0.20, y1=0.55, line=_SILHOUETTE_LINE),
        dict(type="line", x0=0.65, y0=0.82, x1=0.80, y1=0.55, line=_SILHOUETTE_LINE),
        # legs
        dict(type="line", x0=0.42, y0=0.45, x1=0.38, y1=0.05, line=_SILHOUETTE_LINE),
        dict(type="line", x0=0.58, y0=0.45, x1=0.62, y1=0.05, line=_SILHOUETTE_LINE),
    ]


class SelectedPoint(TypedDict):
    body_part: str
    intensity: int


def build_body_map_figure(
    selected_points: Optional[list[SelectedPoint]] = None,
    lang: Language = "en",
) -> go.Figure:
    """Renders the clickable body map. `selected_points` (from
    dcc.Store) colors and labels the currently-selected hotspots;
    everything else renders as a neutral, clickable outline dot.

    Each hotspot marker carries body_part in customdata, so the click
    callback (callbacks/pain_tracking_callbacks.py) can read exactly
    which region was clicked from clickData.
    """
    selected_by_part = {p["body_part"]: p["intensity"] for p in (selected_points or [])}

    xs, ys, colors, sizes, labels, customdata = [], [], [], [], [], []
    for part, (x, y) in BODY_PART_COORDS.items():
        xs.append(x)
        ys.append(y)
        customdata.append(part)
        if part in selected_by_part:
            colors.append(_intensity_color(selected_by_part[part]))
            sizes.append(26)
        else:
            colors.append("#ffffff")
            sizes.append(18)
        labels.append(t(f"body_part.{part}", lang))

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=xs,
            y=ys,
            mode="markers",
            marker=dict(
                size=sizes,
                color=colors,
                line=dict(color="#2c6e9e", width=2),
            ),
            customdata=customdata,
            text=labels,
            hovertemplate="%{text}<extra></extra>",
        )
    )
    fig.update_layout(
        shapes=_silhouette_shapes(),
        xaxis=dict(visible=False, range=[0, 1], fixedrange=True),
        yaxis=dict(visible=False, range=[0, 1], fixedrange=True, scaleanchor="x"),
        margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=420,
        clickmode="event+select",
        showlegend=False,
        dragmode=False,
    )
    return fig
