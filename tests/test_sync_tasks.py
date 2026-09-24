"""Проверки постановки и выполнения фоновой синхронизации."""

from collections.abc import Generator
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from fezzyvig import tasks
from fezzyvig.db.database import get_session
from fezzyvig.main import app
from fezzyvig.models.base import Base
from fezzyvig.models.sync_job import SyncJob
from fezzyvig.models.user import User


def test_sync_api_isolates_jobs(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)

    def session_override() -> Generator[Session, None, None]:
        with Session(engine) as session:
            yield session

    queued = Mock()
    monkeypatch.setattr(tasks.sync_vacancies_task, "apply_async", queued)
    app.dependency_overrides[get_session] = session_override
    try:
        with TestClient(app) as client:
            first = client.post(
                "/auth/register",
                json={
                    "email": "first@example.com",
                    "password": "secret-pass",
                    "first_name": "First",
                    "last_name": "User",
                },
            )
            assert first.status_code == 201
            response = client.post("/employer/sync")
            assert response.status_code == 202
            task_id = response.json()["task_id"]
            assert response.json()["status"] == "queued"
            queued.assert_called_once_with(args=[task_id], task_id=task_id)
            assert client.get(f"/employer/sync/{task_id}").json()["status"] == "queued"

            client.post("/auth/logout")
            second = client.post(
                "/auth/register",
                json={
                    "email": "second@example.com",
                    "password": "secret-pass",
                    "first_name": "Second",
                    "last_name": "User",
                },
            )
            assert second.status_code == 201
            assert client.get(f"/employer/sync/{task_id}").status_code == 404
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


@pytest.mark.parametrize("fails", [False, True])
def test_sync_task_records_outcome(monkeypatch: pytest.MonkeyPatch, fails: bool) -> None:
    engine = create_engine("sqlite://", poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        user = User(email="user@example.com", password_hash="hash")
        session.add(user)
        session.flush()
        session.add(SyncJob(id="job-1", user_id=user.id, status="queued"))
        session.commit()

    async def fake_sync(session: Session, user_id: int) -> int:
        if fails:
            raise ValueError("HH unavailable")
        return 3

    monkeypatch.setattr(tasks, "engine", engine)
    monkeypatch.setattr(tasks, "_sync_vacancies", fake_sync)
    if fails:
        with pytest.raises(ValueError, match="HH unavailable"):
            tasks.sync_vacancies_task.run("job-1")
    else:
        tasks.sync_vacancies_task.run("job-1")

    with Session(engine) as session:
        job = session.get(SyncJob, "job-1")
        assert job is not None
        assert job.status == ("failed" if fails else "succeeded")
        assert job.synced == (None if fails else 3)
    engine.dispose()
