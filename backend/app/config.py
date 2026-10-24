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

    @property
    def is_development(self) -> bool:
        return self.environment.strip().lower() in {"development", "dev", "local", "test"}


settings = Settings()
