"""Application settings loaded from environment variables."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"
PROJECT_ENV_FILE = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    """Runtime configuration for the backend."""

    model_config = SettingsConfigDict(
        env_file=(PROJECT_ENV_FILE, BACKEND_ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    database_url: str = Field(
        default="postgresql+psycopg://username:password@localhost:5432/ai_problem_impact",
        description="SQLAlchemy PostgreSQL connection URL.",
    )
    secret_key: str = Field(
        description="Secret used to sign JWTs; must be supplied by the environment.",
    )
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # ── Similarity / Embedding settings ───────────────────────────────────────
    embedding_enabled: bool = Field(
        default=False,
        description="Set to true to use the real BGE model. False uses mock embeddings.",
    )
    embedding_model: str = Field(
        default="BAAI/bge-small-en-v1.5",
        description="HuggingFace model identifier for BGE embeddings.",
    )
    similarity_threshold: float = Field(
        default=0.75,
        ge=0.0,
        le=1.0,
        description="Minimum cosine similarity to treat two problems as similar.",
    )
    similarity_top_k: int = Field(
        default=5,
        ge=1,
        description="Number of top similar problems to return.",
    )

    @field_validator("database_url", mode="before")
    @classmethod
    def use_psycopg_driver(cls, value: str) -> str:
        """Use the psycopg v3 driver required by this project."""

        for legacy_scheme in ("postgresql://", "postgres://"):
            if value.startswith(legacy_scheme):
                return "postgresql+psycopg://" + value[len(legacy_scheme) :]
        return value


@lru_cache
def get_settings() -> Settings:
    """Return one cached settings instance for the application process."""

    return Settings()