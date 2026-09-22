"""User registration and session authentication endpoints."""

from fastapi import APIRouter, HTTPException, Request, Response, status

from fezzyvig.api.dependencies import SESSION_COOKIE, AuthServiceDependency, CurrentUserDependency
from fezzyvig.api.schemas import AuthCredentials, UserResponse
from fezzyvig.config.settings import get_settings
from fezzyvig.models.user import User
from fezzyvig.services.auth import AuthError

router = APIRouter(prefix="/auth", tags=["auth"])


def _user_response(user: User) -> UserResponse:
    if user.id is None:
        raise RuntimeError("Authenticated user has no id")
    return UserResponse(id=user.id, email=user.email, created_at=user.created_at)


def _set_session_cookie(response: Response, token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=settings.session_lifetime_days * 24 * 60 * 60,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
        path="/",
    )


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(
    credentials: AuthCredentials, response: Response, service: AuthServiceDependency
) -> UserResponse:
    """Register a user and start an authenticated browser session."""
    try:
        user = service.register(credentials.email, credentials.password)
        token = service.create_session(user)
    except AuthError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    _set_session_cookie(response, token)
    return _user_response(user)


@router.post("/login", response_model=UserResponse)
def login(
    credentials: AuthCredentials, response: Response, service: AuthServiceDependency
) -> UserResponse:
    """Authenticate credentials and start a browser session."""
    try:
        user = service.authenticate(credentials.email, credentials.password)
    except AuthError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    _set_session_cookie(response, service.create_session(user))
    return _user_response(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, response: Response, service: AuthServiceDependency) -> None:
    """Revoke the current session and clear its browser cookie."""
    service.delete_session(request.cookies.get(SESSION_COOKIE))
    response.delete_cookie(SESSION_COOKIE, path="/")


@router.get("/me", response_model=UserResponse)
def current_user(user: CurrentUserDependency) -> UserResponse:
    """Return the currently authenticated user."""
    return _user_response(user)
