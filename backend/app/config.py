import json
from pathlib import Path
from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_DIR = Path(__file__).resolve().parent.parent
_DEFAULT_DEV_SECRET = "dev-secret-key-change-in-prod-must-be-at-least-32-chars-long"


class Settings(BaseSettings):
    PROJECT_NAME: str = "Belief Stress Test"
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    DATABASE_URL: str = "sqlite:///./belief_stress_test.db"
    
    SECRET_KEY: str = _DEFAULT_DEV_SECRET
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours
    SESSION_COOKIE_NAME: str = "bst_session"
    COOKIE_SECURE: bool = False
    COOKIE_SAMESITE: str = "lax"

    ADMIN_BOOTSTRAP_SECRET: str = "bootstrap-secret-replace-in-prod"
    INITIAL_ADMIN_USERNAME: str = "admin"
    INITIAL_ADMIN_EMAIL: str = "admin@classroom.edu"
    INITIAL_ADMIN_PASSWORD: str = ""
    
    CORS_ORIGINS: Union[List[str], str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ]
    
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.8-flash"

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def normalize_database_url(cls, v: str) -> str:
        if not v:
            return v
        url = v.strip()
        if url.startswith("postgres://"):
            url = "postgresql+psycopg2://" + url[len("postgres://"):]
        elif url.startswith("postgresql://"):
            url = "postgresql+psycopg2://" + url[len("postgresql://"):]
        return url

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            raw = v.strip()
            if raw.startswith("["):
                try:
                    parsed = json.loads(raw)
                    if isinstance(parsed, list):
                        return [str(i).strip().rstrip("/") for i in parsed if str(i).strip()]
                except Exception:
                    pass
            return [i.strip().rstrip("/") for i in raw.split(",") if i.strip()]
        elif isinstance(v, list):
            return [str(i).strip().rstrip("/") for i in v if str(i).strip()]
        return ["http://localhost:5173"]

    def validate_for_startup(self) -> None:
        """
        Validate required configuration when running in production.
        Raises RuntimeError with a clear message if critical production variables are missing or unsafe.
        """
        if self.ENVIRONMENT.lower() == "production":
            if not self.DATABASE_URL or self.DATABASE_URL.startswith("sqlite"):
                raise RuntimeError(
                    "Production startup blocked: DATABASE_URL must be configured to a managed PostgreSQL database (never SQLite)."
                )
            if not self.SECRET_KEY or self.SECRET_KEY == _DEFAULT_DEV_SECRET or len(self.SECRET_KEY) < 32:
                raise RuntimeError(
                    "Production startup blocked: SECRET_KEY must be set to a unique secret of at least 32 characters."
                )
            origins = self.CORS_ORIGINS if isinstance(self.CORS_ORIGINS, list) else [self.CORS_ORIGINS]
            if not origins or "*" in origins:
                raise RuntimeError(
                    "Production startup blocked: CORS_ORIGINS must specify explicit allowed frontend origins (wildcard '*' is forbidden)."
                )

    model_config = SettingsConfigDict(
        env_file=(str(_BACKEND_DIR / ".env"), ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
if settings.ENVIRONMENT.lower() == "production":
    settings.COOKIE_SECURE = True
    if settings.COOKIE_SAMESITE.lower() == "lax":
        settings.COOKIE_SAMESITE = "none"


