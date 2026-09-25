"""Фоновые задачи синхронизации HeadHunter."""

import asyncio
import logging

import httpx
from celery import Celery  # type: ignore[import-untyped]
from sqlalchemy.orm import Session

from fezzyvig.config.settings import get_settings
from fezzyvig.db.database import engine
from fezzyvig.models.sync_job import SyncJob
from fezzyvig.services.employer import EmployerService

settings = get_settings()
logger = logging.getLogger(__name__)
celery_app = Celery("fezzyvig", broker=settings.celery_broker_url)
celery_app.conf.update(
    task_ignore_result=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
)


async def _sync_vacancies(session: Session, user_id: int) -> int:
    async with httpx.AsyncClient(
        base_url="https://api.hh.ru",
        timeout=httpx.Timeout(settings.http_timeout),
        headers={"HH-User-Agent": settings.hh_user_agent},
    ) as client:
        return await EmployerService(session, client, user_id).sync_vacancies()


@celery_app.task(name="fezzyvig.sync_vacancies")  # type: ignore[untyped-decorator]
def sync_vacancies_task(job_id: str) -> None:
    """Выполнить синхронизацию в отдельной сессии БД и записать итог."""
    with Session(engine) as session:
        job = session.get(SyncJob, job_id)
        if job is None or job.status == "succeeded":
            return
        job.status = "running"
        session.commit()
        try:
            synced = asyncio.run(_sync_vacancies(session, job.user_id))
        except Exception:
            session.rollback()
            job.status = "failed"
            session.commit()
            logger.exception("Employer sync task failed: %s", job_id)
            raise
        job.status = "succeeded"
        job.synced = synced
        session.commit()
