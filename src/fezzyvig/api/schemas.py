"""Схемы запросов и ответов HTTP API."""

from datetime import datetime

from pydantic import BaseModel, Field


class AuthCredentials(BaseModel):
    """Учётные данные для регистрации и входа."""

    email: str
    password: str


class RegistrationCredentials(AuthCredentials):
    """Учётные данные и имя пользователя для регистрации."""

    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)


class UserResponse(BaseModel):
    """Публичное представление аутентифицированного пользователя."""

    id: int
    email: str
    first_name: str | None
    last_name: str | None
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
