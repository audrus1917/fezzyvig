"""Test application route aliases."""

from fezzyvig.api.employer import callback_router, router
from fezzyvig.main import app


def test_main_aliases_oauth_callback() -> None:
    """The public main route uses the OAuth callback handler."""
    callback_endpoints = {
        route.path: route.endpoint
        for route in [*router.routes, *callback_router.routes]
    }

    assert "/main" in app.openapi()["paths"]
    assert callback_endpoints["/main"] is callback_endpoints["/employer/oauth/callback"]
