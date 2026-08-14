"""Layout-level interactivity: sidebar collapse (mobile) and dark mode toggle.

Registered as callbacks on the shared `app` instance — this module must be
imported (for its side effects) after `app` exists, e.g. from app.py:
    from callbacks import layout_callbacks  # noqa: F401
"""
from __future__ import annotations

from dash import Input, Output, State, ctx

from app import app


@app.callback(
    Output("sidebar", "className"),
    Input("sidebar-toggle", "n_clicks"),
    State("sidebar", "className"),
    prevent_initial_call=True,
)
def toggle_sidebar(n_clicks: int, current_class: str) -> str:
    """Only affects mobile/tablet — desktop CSS forces the sidebar visible
    regardless of this class (see assets/style.css breakpoints)."""
    if current_class and "sidebar-open" in current_class:
        return "sidebar"
    return "sidebar sidebar-open"


@app.callback(
    Output("theme-store", "data"),
    Input("theme-toggle", "value"),
    prevent_initial_call=True,
)
def set_theme(is_dark: bool) -> str:
    return "dark" if is_dark else "light"


app.clientside_callback(
    """
    function(theme) {
        document.documentElement.setAttribute('data-theme', theme || 'light');
        return window.dash_clientside.no_update;
    }
    """,
    Output("theme-store", "data", allow_duplicate=True),
    Input("theme-store", "data"),
    prevent_initial_call=True,
)
