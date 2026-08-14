"""Shell layout wrapping every authenticated page: navbar on top,
sidebar + page content below. Individual page bodies are passed in
by the router (app.py) and rendered inside #page-body."""
from __future__ import annotations

from dash import html

from core.i18n import Language
from layouts.navbar import build_navbar
from layouts.sidebar import build_sidebar
from models import User


def build_shell(user: User, lang: Language, active_path: str, page_body) -> html.Div:
    return html.Div(
        dir="rtl" if lang == "fa" else "ltr",
        children=[
            build_navbar(lang, user.role, user.full_name),
            html.Div(
                className="app-body d-flex",
                children=[
                    build_sidebar(user.role, lang, active_path),
                    html.Div(id="page-body", className="flex-grow-1 p-3", children=page_body),
                ],
            ),
        ],
    )
