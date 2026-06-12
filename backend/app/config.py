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

    # --- AI discovery (S3) ---
    # In demo mode (use_mocks) recommendations + matchmaking use a deterministic,
    # keyless local embedding. Set use_mocks=false and provide a key to wire a
    # real embedding/LLM provider (the service accepts an injectable embedder).
    ai_api_key: str = ""
    ai_embedding_model: str = "text-embedding-3-small"

    @property
    def ai_live_enabled(self) -> bool:
        """True only when real AI calls are configured (key present, mocks off)."""
        return bool(self.ai_api_key) and not self.use_mocks

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def google_oauth_enabled(self) -> bool:
        return bool(self.google_client_id and self.google_client_secret)


settings = Settings()
