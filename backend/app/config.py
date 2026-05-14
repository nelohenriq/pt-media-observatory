"""Application configuration via environment variables."""
import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment."""
    project_namespace: str = "pt-media-observatory"
    port: int = int(os.getenv("PORT", "8000"))
    secret_key: str = os.getenv("JWT_SECRET", "super-secret-key-change-me")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    database_url: str = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/ptmedia")

    class Config:
        env_file = ".env"
        extra = "allow"