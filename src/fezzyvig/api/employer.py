"""Эндпоинты OAuth работодателя и синхронизации вакансий HeadHunter."""

from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from kombu.exceptions import OperationalError  # type: ignore[import-untyped]

from fezzyvig.api.dependencies import (
    CurrentUserDependency,
    EmployerServiceDependency,
    SessionDependency,
)
from fezzyvig.api.schemas import EmployerSyncJobResponse, EmployerVacancyResponse
from fezzyvig.config.settings import Settings, get_settings
from fezzyvig.i18n import translate
from fezzyvig.models.sync_job import SyncJob
from fezzyvig.services.employer import EmployerSyncError, InvalidOAuthStateError
from fezzyvig.tasks import sync_vacancies_task

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


def _job_response(job: SyncJob) -> EmployerSyncJobResponse:
    return EmployerSyncJobResponse(task_id=job.id, status=job.status, synced=job.synced)


@router.post("/sync", response_model=EmployerSyncJobResponse, status_code=status.HTTP_202_ACCEPTED)
def employer_sync(
    session: SessionDependency, user: CurrentUserDependency
) -> EmployerSyncJobResponse:
    """Поставить синхронизацию вакансий в очередь Celery."""
    job = SyncJob(id=str(uuid4()), user_id=user.id, status="queued")
    session.add(job)
    session.commit()
    try:
        sync_vacancies_task.apply_async(args=[job.id], task_id=job.id)
    except OperationalError as exc:
        job.status = "failed"
        session.commit()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to queue employer sync",
        ) from exc
    return _job_response(job)


@router.get("/sync/{task_id}", response_model=EmployerSyncJobResponse)
def employer_sync_status(
    task_id: str, session: SessionDependency, user: CurrentUserDependency
) -> EmployerSyncJobResponse:
    """Вернуть состояние только своей задачи синхронизации."""
    job = session.get(SyncJob, task_id)
    if job is None or job.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sync task not found")
    return _job_response(job)
