"""Application configuration."""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings.

    Demo mode (USE_MOCKS) needs no external keys: Google OAuth is optional and the
    app falls back to email/password + seeded demo accounts. Secrets are supplied
    via env / .env (gitignored) or the platform's secret store, never committed.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Convergence Atelier"
    use_mocks: bool = True

    # Persistence: Postgres in prod (5434 on the VPS), SQLite for local/dev + tests.
    database_url: str = "sqlite+aiosqlite:///./convergence.db"

    cors_origins: str = "http://localhost:5173,http://localhost:8095"

    # --- auth ---
    jwt_secret: str = "dev-insecure-change-me-0123456789abcdef"
    jwt_algorithm: str = "HS256"
    access_token_ttl_minutes: int = 720

    # --- Google OAuth (optional; SSO hidden when unset) ---
    google_client_id: str = ""
    google_client_secret: str = ""

    # --- demo seed toggle ---
    seed_demo_data: bool = True

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def google_oauth_enabled(self) -> bool:
        return bool(self.google_client_id and self.google_client_secret)


settings = Settings()
