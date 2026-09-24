"""Эндпоинты OAuth работодателя и синхронизации вакансий HeadHunter."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse

from fezzyvig.api.dependencies import EmployerServiceDependency
from fezzyvig.api.schemas import EmployerSyncResponse, EmployerVacancyResponse
from fezzyvig.config.settings import Settings, get_settings
from fezzyvig.i18n import translate
from fezzyvig.services.employer import EmployerSyncError, InvalidOAuthStateError

router = APIRouter(prefix="/employer", tags=["employer"])
callback_router = APIRouter(tags=["employer"])


@router.get("/oauth/authorize")
def employer_authorize(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
    service: EmployerServiceDependency,
) -> RedirectResponse:
    """Запустить OAuth-авторизацию HeadHunter посредством PKCE."""
    try:
        return RedirectResponse(service.authorization_url(settings, request.app.state.oauth_states))
    except EmployerSyncError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


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
    try:
        await service.complete_authorization(
            code, state, settings, request.app.state.oauth_states
        )
    except InvalidOAuthStateError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
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
