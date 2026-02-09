"""
Application Settings

Environment-based configuration using Pydantic Settings.
"""

import json
import logging
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import model_validator

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Environment
    DEBUG: bool = False
    ENV: str = "development"

    # MongoDB
    MONGODB_URL: str = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "healthbridge"

    # ChromaDB
    CHROMA_PERSIST_DIR: str = "./data/chroma"
    CHROMA_MODE: str = "persistent"  # "persistent" (SQLite) or "http" (server)
    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8001

    # LLM
    LLM_PROVIDER: str = "github"
    LLM_MODEL: str = "openai/gpt-4o-mini"
    LLM_TEMPERATURE: float = 0.3
    GOOGLE_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    GITHUB_TOKEN: str = ""
    GITHUB_BASE_URL: str = "https://models.github.ai/inference"
    AZURE_OPENAI_API_KEY: str = ""

    # Firebase
    FIREBASE_CREDENTIALS_PATH: str = "./firebase-credentials.json"

    # Auth
    SKIP_AUTH: bool = False
    ALLOW_DEV_TOKEN: bool = False
    DEV_TOKEN: Optional[str] = None

    # Opik Tracing
    TRACING_ENABLED: bool = False
    OPIK_API_KEY: str = ""
    OPIK_PROJECT_NAME: str = "health-bridge"
    OPIK_WORKSPACE: str = "default"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # CORS — plain string to avoid pydantic-settings JSON parse issues
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000,http://localhost"

    def get_cors_origins(self) -> List[str]:
        """Parse CORS_ORIGINS into a list. Accepts JSON array or comma-separated."""
        v = self.CORS_ORIGINS.strip()
        if v.startswith("["):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                pass
        return [o.strip() for o in v.split(",") if o.strip()]

    @model_validator(mode="after")
    def _validate_auth_settings(self) -> "Settings":
        """Block dangerous auth settings outside development."""
        if self.SKIP_AUTH and self.ENV != "development":
            raise ValueError(
                "SKIP_AUTH=true is only allowed when ENV=development. "
                f"Current ENV={self.ENV!r}. "
                "Remove SKIP_AUTH or set ENV=development."
            )
        if self.ALLOW_DEV_TOKEN and self.ENV != "development":
            raise ValueError(
                "ALLOW_DEV_TOKEN=true is only allowed when ENV=development. "
                f"Current ENV={self.ENV!r}."
            )
        if self.SKIP_AUTH:
            logger.warning(
                "SKIP_AUTH=true - authentication is BYPASSED. "
                "Do NOT use this in production."
            )
        return self


settings = Settings()
