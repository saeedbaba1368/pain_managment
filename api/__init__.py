"""FastAPI REST service — separate process from the Dash app, sharing the
same SQLAlchemy models / DB / security primitives (see core/).

Run locally with:   uvicorn api.main:api --reload --port 8000
Run in production:  gunicorn api.main:api -k uvicorn.workers.UvicornWorker
"""
