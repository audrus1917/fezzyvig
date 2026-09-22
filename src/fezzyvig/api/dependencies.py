"""Request-scoped application dependencies."""

from datetime import timedelta
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlmodel import Session

from fezzyvig.config.settings import Settings, get_settings
from fezzyvig.db.database import get_session
from fezzyvig.models.user import User
from fezzyvig.services.auth import AuthService
from fezzyvig.services.employer import EmployerService

SESSION_COOKIE = "fezzyvig_session"
SessionDependency = Annotated[Session, Depends(get_session)]


def get_auth_service(
    session: SessionDependency, settings: Annotated[Settings, Depends(get_settings)]
) -> AuthService:
    """Create the request-scoped authentication service."""
    return AuthService(session, timedelta(days=settings.session_lifetime_days))


AuthServiceDependency = Annotated[AuthService, Depends(get_auth_service)]


def get_current_user(request: Request, service: AuthServiceDependency) -> User:
    """Require a valid browser session and return its user."""
    user = service.get_user(request.cookies.get(SESSION_COOKIE))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    return user


CurrentUserDependency = Annotated[User, Depends(get_current_user)]


def get_employer_service(
    request: Request, session: SessionDependency, user: CurrentUserDependency
) -> EmployerService:
    """Создать сервис работодателя, использующий общий клиент HeadHunter."""
    if user.id is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    return EmployerService(session, request.app.state.hh_client, user.id)


EmployerServiceDependency = Annotated[EmployerService, Depends(get_employer_service)]
