"""Application settings loaded from environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class ApplicationSettings(BaseSettings):
    """Runtime configuration. Override any value with an ASTRONAUT_HEALTH_MONITOR_* variable."""

    model_config = SettingsConfigDict(env_prefix="ASTRONAUT_HEALTH_MONITOR_", env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./astronaut_health_monitor.db"
    application_title: str = "Astronaut Health Monitor"
    encryption_key: str | None = None
    encryption_key_file: str = ".data_encryption_key"
    secure_cookies: bool = False
    demo_mode: bool = False


@lru_cache
def get_application_settings() -> ApplicationSettings:
    """Return the cached settings object."""
    return ApplicationSettings()
