"""Доменные модели."""

from fezzyvig.models.oauth_token import EmployerOAuthToken
from fezzyvig.models.user import User, UserSession
from fezzyvig.models.vacancy import EmployerVacancy

__all__ = ["EmployerOAuthToken", "EmployerVacancy", "User", "UserSession"]
