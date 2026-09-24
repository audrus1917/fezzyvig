"""Загрузка типизированных настроек приложения из переменных окружения."""

from functools import lru_cache
from zoneinfo import ZoneInfo

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Настройки времени выполнения, загружаемые из переменных окружения."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://fezzyvig:fezzyvig@localhost:5432/fezzyvig"
    celery_broker_url: str = "redis://localhost:6379/0"
    log_level: str = "INFO"
    http_timeout: float = Field(default=10.0, gt=0)
    hh_user_agent: str = "Fezzyvig/0.1 you@sample.com"
    hh_client_id: str | None = None
    hh_client_secret: SecretStr | None = None
    hh_redirect_uri: str | None = None
    hh_employer_id: str | None = None
    session_cookie_secure: bool = False
    session_lifetime_days: int = Field(default=30, ge=1, le=365)
    tz_name: str = "Europe/Minsk"
    tz_offset: int = 3

    @property
    def TZ(self) -> ZoneInfo:
        """Возвращает таймзону."""

        return ZoneInfo(self.tz_name)


@lru_cache
def get_settings() -> Settings:
    """Вернуть общий для процесса экземпляр проверенных настроек."""
    return Settings()
