"""Left sidebar navigation. Full-width and always visible on desktop
(>=1024px); collapsible drawer on mobile/tablet, toggled by the navbar
hamburger button (see callbacks/layout_callbacks.py)."""
from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import html

from core.i18n import Language, t
from models import UserRole

# (icon class, translation key, href, roles allowed)
NAV_ITEMS = [
    ("bi-speedometer2", "nav.dashboard", "/dashboard", {UserRole.ADMIN, UserRole.DOCTOR, UserRole.NURSE}),
    ("bi-people", "nav.patients", "/patients", {UserRole.ADMIN, UserRole.DOCTOR, UserRole.NURSE}),
    (
        "bi-clipboard2-pulse",
        "nav.pain_tracking",
        "/pain-tracking",
        {UserRole.ADMIN, UserRole.DOCTOR, UserRole.NURSE},
    ),
    ("bi-capsule", "nav.medications", "/medications", {UserRole.ADMIN, UserRole.DOCTOR, UserRole.NURSE}),
    (
        "bi-calendar-check",
        "nav.appointments",
        "/appointments",
        {UserRole.ADMIN, UserRole.DOCTOR, UserRole.NURSE},
    ),
    ("bi-file-earmark-bar-graph", "nav.reports", "/reports", {UserRole.ADMIN, UserRole.DOCTOR}),
]


def build_sidebar(role: UserRole, lang: Language, active_path: str) -> html.Div:
    links = [
        dbc.NavLink(
            [html.I(className=f"bi {icon} me-2"), t(label_key, lang)],
            href=href,
            active=active_path == href,
            className="sidebar-link",
        )
        for icon, label_key, href, allowed_roles in NAV_ITEMS
        if role in allowed_roles
    ]

    return html.Div(
        id="sidebar",
        className="sidebar sidebar-open",  # 'sidebar-open' default on desktop; JS/callback toggles on mobile
        children=[dbc.Nav(links, vertical=True, pills=True, className="p-2")],
    )
