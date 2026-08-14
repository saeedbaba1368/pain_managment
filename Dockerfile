# Shared image for both services defined in docker-compose.yml (`app` and `api`) —
# same codebase and dependencies, only the CMD differs (see docker-compose.yml).
FROM python:3.12-slim AS base

# System packages:
#   libpq-dev / gcc        -> psycopg2 build
#   libpango/libcairo/etc. -> WeasyPrint (PDF generation via HTML/CSS)
#   fonts-liberation        -> baseline PDF font fallback (Vazirmatn TTF, if
#                              provided in assets/, is used automatically —
#                              see utils/pdf_generator.py)
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        libpango-1.0-0 \
        libpangocairo-1.0-0 \
        libcairo2 \
        libgdk-pixbuf2.0-0 \
        libffi-dev \
        shared-mime-info \
        fonts-liberation \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Runs as non-root in production.
RUN useradd --create-home --uid 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8050 8000

# Default command runs the Dash app; docker-compose.yml overrides this for
# the `api` service to run uvicorn/gunicorn against api.main:api instead.
CMD ["gunicorn", "app:server", "--bind", "0.0.0.0:8050", "--workers", "4", "--timeout", "120"]
