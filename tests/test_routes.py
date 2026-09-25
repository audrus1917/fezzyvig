"""Тесты альтернативных маршрутов приложения."""

from fastapi.testclient import TestClient

from fezzyvig.api.employer import callback_router, router
from fezzyvig.main import app


def test_main_aliases_oauth_callback() -> None:
    """Публичный маршрут main использует обработчик ответа OAuth."""
    callback_endpoints = {
        route.path: route.endpoint
        for route in [*router.routes, *callback_router.routes]
    }

    assert "/main" in app.openapi()["paths"]
    assert callback_endpoints["/main"] is callback_endpoints["/employer/oauth/callback"]


def test_login_page() -> None:
    """Отдельный адрес входа возвращает frontend."""
    with TestClient(app) as client:
        response = client.get("/login")

    assert response.status_code == 200
    assert "<div id=\"app\"></div>" in response.text


def test_vacancy_page() -> None:
    """Прямая ссылка на карточку возвращает frontend."""
    with TestClient(app) as client:
        response = client.get("/vacancies/42")

    assert response.status_code == 200
    assert "<div id=\"app\"></div>" in response.text
