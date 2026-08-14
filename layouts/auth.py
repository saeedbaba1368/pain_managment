"""Login page — the only page an unauthenticated user can ever see.

Supports a language toggle (fa/en) even before login, since patients
default to Persian and staff to English but either can switch here.
"""
from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import dcc, html

from core.i18n import Language, t


def login_layout(lang: Language = "en") -> html.Div:
    is_rtl = lang == "fa"

    return html.Div(
        className="auth-page d-flex align-items-center justify-content-center vh-100",
        dir="rtl" if is_rtl else "ltr",
        children=[
            dbc.Card(
                className="p-4 shadow-sm",
                style={"maxWidth": "380px", "width": "100%"},
                children=[
                    html.Div(
                        className="d-flex justify-content-between align-items-center mb-3",
                        children=[
                            html.H4(t("app.title", lang), className="mb-0"),
                            dbc.RadioItems(
                                id="login-lang-toggle",
                                options=[
                                    {"label": "FA", "value": "fa"},
                                    {"label": "EN", "value": "en"},
                                ],
                                value=lang,
                                inline=True,
                                inputClassName="btn-check",
                                labelClassName="btn btn-outline-secondary btn-sm",
                                className="btn-group",
                            ),
                        ],
                    ),
                    dbc.Label(t("auth.username", lang)),
                    dbc.Input(id="login-username", type="text", className="mb-3", autoFocus=True),
                    dbc.Label(t("auth.password", lang)),
                    dbc.Input(id="login-password", type="password", className="mb-3", n_submit=0),
                    dbc.Button(
                        t("auth.login", lang),
                        id="login-submit",
                        color="primary",
                        className="w-100 mb-2",
                        n_clicks=0,
                    ),
                    html.Div(id="login-error"),
                ],
            )
        ],
    )
