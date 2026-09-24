"""Эндпоинты OAuth работодателя и синхронизации вакансий HeadHunter."""

import logging

from datetime import UTC, datetime
from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse

from fezzyvig.api.dependencies import CurrentUserDependency, EmployerServiceDependency
from fezzyvig.api.schemas import EmployerSyncResponse, EmployerVacancyResponse
from fezzyvig.config.settings import Settings, get_settings
from fezzyvig.i18n import translate
from fezzyvig.services.employer import EmployerService, EmployerSyncError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/employer", tags=["employer"])
callback_router = APIRouter(tags=["employer"])


@router.get("/oauth/authorize")
def employer_authorize(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
    user: CurrentUserDependency,
) -> RedirectResponse:
    """Запустить OAuth-авторизацию HeadHunter посредством PKCE."""
    if not settings.hh_client_id or not settings.hh_redirect_uri:
        raise HTTPException(status_code=500, detail="HH OAuth is not configured")
    state, verifier, challenge = EmployerService.create_pkce()
    request.app.state.oauth_states[state] = (
        verifier,
        datetime.now(UTC).timestamp() + 600,
        user.id,
    )
    url = (
        "https://hh.ru/oauth/authorize?response_type=code&client_id="
        + quote(settings.hh_client_id)
        + "&redirect_uri="
        + quote(settings.hh_redirect_uri)
        + "&state="
        + state
        + "&code_challenge="
        + challenge
        + "&code_challenge_method=S256"
    )
    return RedirectResponse(url)


@callback_router.get("/main")
@router.get("/oauth/callback")
async def employer_callback(
    request: Request,
    code: str,
    state: str,
    settings: Annotated[Settings, Depends(get_settings)],
    service: EmployerServiceDependency,
) -> dict[str, str]:
    """Обменять корректный ответ OAuth HeadHunter и сохранить токены."""
    stored = request.app.state.oauth_states.pop(state, None)
    if (
        not stored
        or stored[1] < datetime.now(UTC).timestamp()
        or stored[2] != service.user_id
        or not settings.hh_client_id
        or not settings.hh_client_secret
        or not settings.hh_redirect_uri
    ):
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state")
    try:
        await service.exchange_code(
            code,
            stored[0],
            settings.hh_client_id,
            settings.hh_client_secret.get_secret_value(),
            settings.hh_redirect_uri,
        )
    except EmployerSyncError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {"status": "connected", "message": translate(request, "HH employer account connected")}


@router.get("/vacancies", response_model=list[EmployerVacancyResponse])
def employer_vacancies(
    service: EmployerServiceDependency,
) -> list[EmployerVacancyResponse]:
    """Вернуть локально синхронизированные вакансии работодателя."""
    return [
        EmployerVacancyResponse.model_validate(vacancy, from_attributes=True)
        for vacancy in service.list_vacancies()
    ]


@router.post("/sync", response_model=EmployerSyncResponse)
async def employer_sync(service: EmployerServiceDependency) -> EmployerSyncResponse:
    """Синхронизировать вакансии из HeadHunter."""
    try:
        return EmployerSyncResponse(synced=await service.sync_vacancies())
    except EmployerSyncError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
