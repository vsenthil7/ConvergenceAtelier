"""Application configuration."""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings. Demo mode (USE_MOCKS) needs no external keys."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Convergence Atelier"
    use_mocks: bool = True
    database_url: str = "sqlite+aiosqlite:///./convergence.db"
    cors_origins: str = "http://localhost:5173,http://localhost:8095"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
