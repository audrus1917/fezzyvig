"""Схемы запросов и ответов HTTP API."""

from datetime import datetime

from pydantic import BaseModel


class AuthCredentials(BaseModel):
    """Учётные данные для регистрации и входа."""

    email: str
    password: str


class UserResponse(BaseModel):
    """Публичное представление аутентифицированного пользователя."""

    id: int
    email: str
    created_at: datetime


class EmployerVacancyResponse(BaseModel):
    """Вакансия работодателя, возвращаемая API."""

    id: int
    external_id: str
    title: str
    company: str
    url: str
    description: str
    published_at: datetime | None
    synced_at: datetime


class EmployerSyncResponse(BaseModel):
    """Сводный результат синхронизации вакансий работодателя."""

    synced: int
