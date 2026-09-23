"""Тесты загрузки и проверки настроек приложения."""

import pytest
from pydantic import ValidationError

from fezzyvig.config.settings import Settings, get_settings


def test_settings_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Переменные окружения преобразуются в типизированные настройки."""
    monkeypatch.setenv("HTTP_TIMEOUT", "2.5")
    monkeypatch.setenv("SESSION_COOKIE_SECURE", "true")
    monkeypatch.setenv("HH_CLIENT_SECRET", "test-secret")
    monkeypatch.setenv("TZ_NAME", "UTC")

    settings = Settings(_env_file=None)

    assert settings.http_timeout == 2.5
    assert settings.session_cookie_secure is True
    assert settings.hh_client_secret is not None
    assert settings.hh_client_secret.get_secret_value() == "test-secret"
    assert settings.TZ.key == "UTC"


@pytest.mark.parametrize(
    ("name", "value"),
    [("http_timeout", 0), ("session_lifetime_days", 0), ("session_lifetime_days", 366)],
)
def test_settings_reject_invalid_values(
    monkeypatch: pytest.MonkeyPatch, name: str, value: int
) -> None:
    """Недопустимые значения ограниченных настроек отклоняются."""
    monkeypatch.setenv(name.upper(), str(value))

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_get_settings_is_cached(monkeypatch: pytest.MonkeyPatch) -> None:
    """Настройки перечитываются после очистки кэша."""
    get_settings.cache_clear()
    try:
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")
        first = get_settings()
        monkeypatch.setenv("LOG_LEVEL", "WARNING")

        assert get_settings() is first
        assert get_settings().log_level == "DEBUG"

        get_settings.cache_clear()
        assert get_settings().log_level == "WARNING"
    finally:
        get_settings.cache_clear()
