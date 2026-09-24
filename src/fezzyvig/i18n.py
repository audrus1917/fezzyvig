"""Переводить сообщения API для языка HTTP-запроса."""

import gettext
from pathlib import Path

from fastapi import Request

LOCALE_DIR = Path(__file__).parent / "locale"


def translate(request: Request, message: str) -> str:
    """Вернуть перевод сообщения для предпочтительного языка запроса."""
    
    preferences: list[tuple[float, int, str]] = []
    for order, item in enumerate(request.headers.get("accept-language", "").split(",")):
        language, _, parameters = item.strip().partition(";")
        quality = 1.0
        for parameter in parameters.split(";"):
            if parameter.strip().startswith("q="):
                try:
                    quality = float(parameter.strip()[2:])
                except ValueError:
                    quality = 0.0
        if 0 < quality <= 1:
            preferences.append((quality, order, language.lower().split("-", 1)[0]))

    for _, _, language in sorted(preferences, key=lambda value: (-value[0], value[1])):
        if language in {"ru", "en"}:
            translations = gettext.translation(
                "fezzyvig", localedir=LOCALE_DIR, languages=[language], fallback=True
            )
            return translations.gettext(message)
    return message
