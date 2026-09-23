"""Тесты альтернативных маршрутов приложения."""

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
