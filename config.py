"""
Central configuration for the Pain Management Dashboard.

All values are loaded from environment variables (see .env.example).
Uses pydantic-settings so misconfiguration fails fast at startup
rather than silently at runtime.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Strongly-typed application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- App ---
    APP_NAME: str = "Pain Management Dashboard"
    APP_ENV: Literal["development", "staging", "production"] = "development"
    DEBUG: bool = False
    SECRET_KEY: str = Field(..., min_length=32, description="Flask session secret")
    HOST: str = "0.0.0.0"
    PORT: int = 8050

    # --- Database ---
    DATABASE_URL: PostgresDsn
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 1800  # seconds, avoids stale connections

    # --- Auth / JWT (used by FastAPI service) ---
    JWT_SECRET_KEY: str = Field(..., min_length=32)
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # --- Session / security ---
    SESSION_TIMEOUT_MINUTES: int = 20  # auto-logout after inactivity
    BCRYPT_ROUNDS: int = 12
    FIELD_ENCRYPTION_KEY: str = Field(
        ..., min_length=32, description="Fernet key for encrypting PII columns"
    )

    # --- CORS (FastAPI) ---
    CORS_ORIGINS: list[str] = ["http://localhost:8050"]

    # --- Rate limiting ---
    RATE_LIMIT_DEFAULT: str = "100/minute"
    RATE_LIMIT_LOGIN: str = "5/minute"

    # --- i18n ---
    DEFAULT_LANGUAGE: Literal["fa", "en"] = "en"
    SUPPORTED_LANGUAGES: tuple[str, ...] = ("fa", "en")

    # --- Alerts ---
    HIGH_PAIN_VAS_THRESHOLD: int = 8
    OPIOID_ALERT_DAYS_WINDOW: int = 30

    # --- Backups ---
    BACKUP_DIR: str = "/backups"
    BACKUP_RETENTION_DAYS: int = 30

    # --- Map / geolocation ---
    MAPBOX_TOKEN: str = ""
    DEFAULT_MAP_CENTER_LAT: float = 35.6892  # Tehran
    DEFAULT_MAP_CENTER_LON: float = 51.3890

    @field_validator("SECRET_KEY", "JWT_SECRET_KEY", "FIELD_ENCRYPTION_KEY")
    @classmethod
    def _no_default_secrets(cls, v: str) -> str:
        if v.lower() in {"changeme", "secret", "test"}:
            raise ValueError("Refusing to start with a placeholder secret value.")
        return v

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"


@lru_cache
def get_settings() -> Settings:
    """Cached settings accessor — import and call this, don't instantiate Settings() directly."""
    return Settings()


settings = get_settings()
