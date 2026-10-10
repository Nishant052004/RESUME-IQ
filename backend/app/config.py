"""Application configuration (Module 8 — env/config management).

All values can be overridden via environment variables or a `.env` file
placed in the `backend/` directory. See `.env.example` at the project root.
"""
from pathlib import Path

from pydantic_settings import BaseSettings

BACKEND_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    APP_NAME: str = "ResumeIQ"
    # Default to a file-based SQLite DB so the app runs with zero setup.
    # Set DATABASE_URL=postgresql+psycopg2://user:pass@host:5432/resumeiq for Postgres.
    DATABASE_URL: str = f"sqlite:///{BACKEND_DIR / 'resumeiq.db'}"

    JWT_SECRET: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # OAuth sign-in (Google / GitHub). Register these in each provider's
    # console with the redirect URI printed by /api/auth/oauth/{provider}
    # (…/api/auth/oauth/{provider}/callback). Empty = button shows a
    # "not configured" hint instead of breaking.
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GITHUB_CLIENT_ID: str = ""
    GITHUB_CLIENT_SECRET: str = ""
    OAUTH_STATE_TTL_MINUTES: int = 10

    # Optional LLM enhancement. When LLM_API_KEY is empty the pipeline falls
    # back to the deterministic (lexicon + TF-IDF) engine, so no key is required.
    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = "https://api.openai.com/v1"
    LLM_MODEL: str = "gpt-4o-mini"

    # Default scoring weights (auto-normalised to 100% at runtime).
    DEFAULT_WEIGHTS: dict = {
        "skills": 40,
        "experience": 25,
        "projects": 15,
        "education": 10,
        "certifications": 10,
    }

    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173"

    class Config:
        env_file = str(BACKEND_DIR / ".env")
        env_file_encoding = "utf-8"


settings = Settings()
