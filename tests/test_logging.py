"""Тесты настройки журналирования приложения."""

import logging
import sys
from typing import Any

import pytest

from fezzyvig.main import configure_logging


def test_logging_uses_stdout(monkeypatch: pytest.MonkeyPatch) -> None:
    """Журналы приложения отправляются в стандартный вывод контейнера."""
    options: dict[str, Any] = {}

    def capture_options(**kwargs: Any) -> None:
        options.update(kwargs)

    monkeypatch.setattr(logging, "basicConfig", capture_options)

    configure_logging("info")

    assert options["level"] == "INFO"
    assert options["stream"] is sys.stdout
    assert options["force"] is True
