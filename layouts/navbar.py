"""Top navbar. Hamburger toggles the sidebar on mobile/tablet; language switch
is only shown to staff (admin/nurse) since doctor UI is English-only and
patient UI is Persian-only per the role table."""
from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import html

from core.i18n import Language, t
from models import UserRole


def build_navbar(lang: Language, role: UserRole, full_name: str) -> dbc.Navbar:
    show_lang_switch = role in (UserRole.ADMIN, UserRole.NURSE)

    right_items = []
    if show_lang_switch:
        right_items.append(
            dbc.RadioItems(
                id="navbar-lang-toggle",
                options=[{"label": "FA", "value": "fa"}, {"label": "EN", "value": "en"}],
                value=lang,
                inline=True,
                inputClassName="btn-check",
                labelClassName="btn btn-outline-light btn-sm",
                className="btn-group me-3",
            )
        )

    right_items += [
        dbc.Switch(id="theme-toggle", label="🌙", className="me-3 text-white", value=False),
        dbc.DropdownMenu(
            label=full_name,
            color="link",
            align_end=True,
            children=[
                dbc.DropdownMenuItem(t("nav.logout", lang), href="/logout", external_link=True),
            ],
        ),
    ]

    return dbc.Navbar(
        dbc.Container(
            fluid=True,
            children=[
                html.Div(
                    className="d-flex align-items-center",
                    children=[
                        dbc.Button(
                            html.I(className="bi bi-list"),
                            id="sidebar-toggle",
                            color="link",
                            className="text-white me-2 d-lg-none",
                            n_clicks=0,
                        ),
                        dbc.NavbarBrand(t("app.title", lang), href="/dashboard", className="text-white"),
                    ],
                ),
                html.Div(className="d-flex align-items-center", children=right_items),
            ],
        ),
        color="primary",
        dark=True,
        sticky="top",
        className="mb-0",
    )
