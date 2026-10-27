from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_prefix="", case_sensitive=False)

    app_name: str = "PRAMAAN-AICTE"
    environment: str = "development"
    log_level: str = "INFO"
    database_url: str = "postgresql://localhost:5432/pramaan"
    secret_key: str = ""
    cors_origins: str = "http://localhost:5173"
    max_upload_size_mb: int = 5
    allowed_upload_extensions: str = ".csv"
    upload_dir: str = "uploads"
    # PBKDF2 work factor. An engineering parameter, not a compliance claim.
    password_hash_iterations: int = 600_000
    # Server-side session lifetime.
    session_ttl_hours: int = 12
    # Set to 1 outside local development so the session cookie is Secure.
    cookie_secure: bool = False

    @property
    def is_development(self) -> bool:
        return self.environment.strip().lower() in {"development", "dev", "local", "test"}


settings = Settings()
