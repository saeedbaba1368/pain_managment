"""
FastAPI REST service entry point — serves the mobile app / third-party
integrations. Separate process from the Dash app (app.py); shares the same
Postgres database and SQLAlchemy models via core/.

Run locally:   uvicorn api.main:api --reload --port 8000
Run in Docker: see docker-compose.yml (service `api`)
Docs:          GET /docs (Swagger UI), GET /redoc, GET /openapi.json
"""
from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from api import auth
from api.deps import limiter
from api.endpoints import appointments, medications, pain_records, patients, reports, vitals
from config import settings

api = FastAPI(
    title=settings.APP_NAME,
    description="REST API for the Pain Management Dashboard mobile app and integrations.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# --- Rate limiting (slowapi / Redis-free in-memory limiter; default per config.RATE_LIMIT_DEFAULT) ---
api.state.limiter = limiter
api.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# --- CORS: only the origins listed in settings.CORS_ORIGINS may call this API from a browser ---
api.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api.include_router(auth.router)
api.include_router(patients.router)
api.include_router(pain_records.router)
api.include_router(medications.router)
api.include_router(vitals.router)
api.include_router(appointments.router)
api.include_router(reports.router)


@api.get("/health", tags=["health"])
def health() -> dict:
    """Liveness probe for Docker/orchestrator health checks — no auth required."""
    return {"status": "ok", "app": settings.APP_NAME, "env": settings.APP_ENV}


@api.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Last-resort handler so an unexpected error never leaks a stack trace
    or internal detail to the client — full traceback still goes to logs."""
    import logging

    logging.getLogger("api").exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )
