from app.config import Settings


def test_settings_load_defaults() -> None:
    settings = Settings()
    assert settings.app_name == "PRAMAAN-AICTE"
    assert settings.environment == "development"
    assert settings.log_level == "INFO"


def test_settings_read_environment(monkeypatch) -> None:
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("APP_ENV", "development")
    settings = Settings()
    assert settings.log_level == "DEBUG"


def test_settings_cors_origins_default(monkeypatch) -> None:
    monkeypatch.delenv("CORS_ORIGINS", raising=False)
    assert Settings().cors_origins == "http://localhost:5173"


def test_settings_cors_origins_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:5173, https://example.local")
    settings = Settings()
    assert settings.cors_origins == "http://localhost:5173, https://example.local"
