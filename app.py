"""
Application entry point. Wires together the Flask server, Flask-Login,
and the Dash app shell (routing container that swaps pages based on
auth state and URL — individual page layouts live in layouts/).

Run locally with:  python app.py
Run in production:  gunicorn app:server
"""
from __future__ import annotations

from datetime import datetime, timezone

import dash
import dash_bootstrap_components as dbc
from dash import Dash, Input, Output, State, dcc, html
from flask import Flask, redirect, session
from flask_login import LoginManager, current_user, login_user, logout_user

from config import settings
from core.database import session_scope
from core.i18n import t
from core.security import verify_password
from layouts.app_shell import build_shell
from layouts.auth import login_layout
from layouts.dashboard import build_dashboard
from layouts.pain_tracking import build_pain_tracking
from models import User, UserRole

# ---------------------------------------------------------------------------
# Flask server + Flask-Login
# ---------------------------------------------------------------------------

server = Flask(__name__)
server.config["SECRET_KEY"] = settings.SECRET_KEY
server.config["PERMANENT_SESSION_LIFETIME"] = settings.SESSION_TIMEOUT_MINUTES * 60
server.config["SESSION_COOKIE_HTTPONLY"] = True
server.config["SESSION_COOKIE_SAMESITE"] = "Lax"
server.config["SESSION_COOKIE_SECURE"] = settings.is_production

login_manager = LoginManager()
login_manager.init_app(server)
login_manager.login_view = "/login"


@login_manager.user_loader
def load_user(user_id: str) -> User | None:
    """Flask-Login calls this on every request to hydrate current_user."""
    with session_scope() as db:
        user = db.get(User, int(user_id))
        if user is not None:
            db.expunge(user)  # detach so it's usable outside the closed session
        return user


# ---------------------------------------------------------------------------
# Dash app shell
# ---------------------------------------------------------------------------

app: Dash = dash.Dash(
    __name__,
    server=server,
    external_stylesheets=[dbc.themes.FLATLY, "/assets/style.css"],
    suppress_callback_exceptions=True,  # page layouts are registered dynamically per-route
    title=settings.APP_NAME,
    update_title=None,
)

app.layout = html.Div(
    [
        dcc.Location(id="url", refresh=False),
        dcc.Store(id="session-lang", storage_type="session", data=settings.DEFAULT_LANGUAGE),
        dcc.Store(id="theme-store", storage_type="local", data="light"),
        html.Div(id="page-content"),
    ]
)


# ROLE_HOME_ROUTE maps each role to its landing page after login.
ROLE_HOME_ROUTE = {
    UserRole.ADMIN: "/dashboard",
    UserRole.DOCTOR: "/dashboard",
    UserRole.NURSE: "/dashboard",
    UserRole.PATIENT: "/self-report",
}


@app.callback(
    Output("session-lang", "data"),
    Input("login-lang-toggle", "value"),
    prevent_initial_call=True,
)
def set_language(value: str) -> str:
    """Language toggle on the login page updates the session store, which
    re-renders the page below (session-lang is an Input on route())."""
    return value


@app.callback(
    Output("page-content", "children"),
    Input("url", "pathname"),
    Input("session-lang", "data"),
)
def route(pathname: str, lang: str):
    """Top-level router: unauthenticated users only ever see the login page.
    Page layouts for /dashboard, /patients, /self-report, etc. are registered
    by their respective layouts/*.py modules (see later modules) and imported
    here as they're built.
    """
    if not current_user.is_authenticated:
        return login_layout(lang=lang or settings.DEFAULT_LANGUAGE)

    if pathname in (None, "/", "/login"):
        return dcc.Location(pathname=ROLE_HOME_ROUTE[current_user.role], id="redirect-home")

    # Page body: real layouts wired in as built; remaining routes still placeholder (modules 8-9).
    if pathname == "/dashboard":
        page_body = build_dashboard(lang)
    elif pathname == "/pain-tracking":
        # Same role gate as the sidebar entry (layouts/sidebar.py NAV_ITEMS);
        # the write path itself is separately enforced in
        # callbacks/pain_tracking_callbacks.py via @require_role.
        if current_user.role.value not in ("admin", "doctor", "nurse"):
            page_body = dbc.Alert(f"Route {pathname} not permitted for this role.", color="danger")
        else:
            page_body = build_pain_tracking(lang)
    else:
        page_body = dbc.Alert(f"Route {pathname} not yet implemented.", color="warning")
    return build_shell(user=current_user, lang=lang, active_path=pathname, page_body=page_body)


@app.callback(
    Output("session-lang", "data", allow_duplicate=True),
    Input("navbar-lang-toggle", "value"),
    prevent_initial_call=True,
)
def set_language_navbar(value: str) -> str:
    """Same store as the login toggle (layouts/auth.py) — separate callback
    because the component only exists post-login, for admin/nurse roles."""
    return value


@app.callback(
    Output("url", "pathname"),
    Output("login-error", "children"),
    Input("login-submit", "n_clicks"),
    State("login-username", "value"),
    State("login-password", "value"),
    State("session-lang", "data"),
    prevent_initial_call=True,
)
def handle_login(n_clicks: int, username: str, password: str, lang: str):
    """Validates credentials, starts the Flask-Login session, redirects by role."""
    lang = lang or settings.DEFAULT_LANGUAGE
    if not username or not password:
        return dash.no_update, dbc.Alert(t("auth.invalid_credentials", lang), color="danger")

    with session_scope() as db:
        user = db.query(User).filter(User.username == username, User.is_active.is_(True)).first()
        if user is None or not verify_password(password, user.password_hash):
            # Deliberately vague error — don't reveal whether the username exists.
            return dash.no_update, dbc.Alert(t("auth.invalid_credentials", lang), color="danger")

        login_user(user)
        session.permanent = True  # activates PERMANENT_SESSION_LIFETIME (SESSION_TIMEOUT_MINUTES)
        # so inactivity actually expires the session -- without this the cookie
        # has no server-enforced expiry and SESSION_TIMEOUT_MINUTES is a no-op.
        user.last_login = datetime.now(timezone.utc)
        db.add(user)

    return ROLE_HOME_ROUTE[user.role], ""


@server.route("/logout")
def logout():
    logout_user()
    return redirect("/login")


# Imported for side effects (registers callbacks on `app`).
# Must come after `app` is defined above — these modules do `from app import app`.
from callbacks import layout_callbacks  # noqa: E402, F401
from callbacks import dashboard_callbacks  # noqa: E402, F401
from callbacks import pain_tracking_callbacks  # noqa: E402, F401

if __name__ == "__main__":
    app.run(debug=settings.DEBUG, host=settings.HOST, port=settings.PORT)
