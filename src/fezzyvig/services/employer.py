"""OAuth работодателя и синхронизация данных HeadHunter."""

import base64
import hashlib
import logging
import secrets
from collections.abc import MutableMapping
from datetime import UTC, datetime, timedelta
from typing import cast
from urllib.parse import quote

import httpx
from sqlalchemy.orm import Session

from fezzyvig.config.settings import Settings, get_settings
from fezzyvig.models.oauth_token import EmployerOAuthToken
from fezzyvig.models.vacancy import EmployerVacancy
from fezzyvig.repositories.employer import EmployerRepository

settings = get_settings()
logger = logging.getLogger(__name__)


class EmployerSyncError(RuntimeError):
    """Ошибка синхронизации данных работодателя через HeadHunter."""


class InvalidOAuthStateError(EmployerSyncError):
    """Состояние OAuth отсутствует, истекло или принадлежит другому пользователю."""


class EmployerService:
    """Синхронизация вакансий работодателя без записи данных в HeadHunter."""

    def __init__(self, session: Session, client: httpx.AsyncClient, user_id: int) -> None:
        """Инициализировать сервис для конкретного пользователя."""
        self._session = session
        self._repository = EmployerRepository(session, user_id)
        self._client = client
        self.user_id = user_id

    @staticmethod
    def create_pkce() -> tuple[str, str, str]:
        """Создать состояние OAuth, верификатор и S256-проверку кода."""
        verifier = secrets.token_urlsafe(64)
        challenge = (
            base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
            .decode()
            .rstrip("=")
        )
        return secrets.token_urlsafe(32), verifier, challenge

    def authorization_url(
        self, settings: Settings, oauth_states: MutableMapping[str, tuple[str, float, int]]
    ) -> str:
        """Сформировать ссылку авторизации и сохранить временное состояние OAuth."""
        if not settings.hh_client_id or not settings.hh_redirect_uri:
            raise EmployerSyncError("HH OAuth is not configured")
        state, verifier, challenge = self.create_pkce()
        oauth_states[state] = (verifier, datetime.now(UTC).timestamp() + 600, self.user_id)
        return (
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

    async def complete_authorization(
        self,
        code: str,
        state: str,
        settings: Settings,
        oauth_states: MutableMapping[str, tuple[str, float, int]],
    ) -> None:
        """Проверить состояние OAuth и сохранить выданные токены."""
        stored = oauth_states.pop(state, None)
        if (
            not stored
            or stored[1] < datetime.now(UTC).timestamp()
            or stored[2] != self.user_id
            or not settings.hh_client_id
            or not settings.hh_client_secret
            or not settings.hh_redirect_uri
        ):
            raise InvalidOAuthStateError("Invalid or expired OAuth state")
        await self.exchange_code(
            code,
            stored[0],
            settings.hh_client_id,
            settings.hh_client_secret.get_secret_value(),
            settings.hh_redirect_uri,
        )

    async def exchange_code(
        self,
        code: str,
        verifier: str,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
    ) -> str:
        """Обменять код авторизации OAuth и сохранить полученную пару токенов."""
        try:
            response = await self._client.post(
                "/token",
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "redirect_uri": redirect_uri,
                    "code_verifier": verifier,
                },
            )
            response.raise_for_status()
            tokens = self._parse_tokens(response)
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
            raise EmployerSyncError("HH OAuth token exchange failed") from exc
        self._store_tokens(*tokens)
        return tokens[0]

    async def sync_vacancies(self, vacancies_url: str | None = None) -> int:
        """Синхронизировать вакансии работодателя в локальном хранилище.
        
        
        """
        try:
            access_token = await self._get_access_token()

            # Формируем ссылку или используем перданную в параметрах
            employer_id = settings.hh_employer_id
            vacancies_url = vacancies_url or f"/employers/{employer_id}/vacancies/active"

            response = await self._client.get(
                vacancies_url,
                headers=self._authorization_headers(access_token),
            )

            logger.debug(response)
            if self._is_token_expired(response):
                access_token = await self._refresh_access_token(access_token)
                response = await self._client.get(
                    "/employer/vacancies",
                    headers=self._authorization_headers(access_token),
                )
            response.raise_for_status()
            payload = response.json()
            items = payload.get("items", [])
            if not isinstance(items, list):
                raise ValueError("items must be a list")
        except EmployerSyncError:
            raise
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            raise EmployerSyncError("Unable to load employer vacancies from HH") from exc

        synced = 0
        for item in items:
            if not isinstance(item, dict) or "id" not in item:
                continue
            external_id = str(item["id"])
            record = self._repository.get_vacancy(external_id)
            if record is None:
                record = EmployerVacancy(
                    user_id=self.user_id,
                    external_id=external_id,
                    title=str(item.get("name", "")),
                    company=str((item.get("employer") or {}).get("name", "")),
                    url=str(item.get("alternate_url", "")),
                    description=str(item.get("snippet", {}).get("requirement", "")),
                )
            record.title = str(item.get("name", record.title))
            record.company = str((item.get("employer") or {}).get("name", record.company))
            record.url = str(item.get("alternate_url", record.url))
            record.raw_payload = cast(dict[str, object], item)
            record.synced_at = datetime.now(UTC)
            self._repository.save_vacancy(record)
            synced += 1
        self._session.commit()
        return synced

    def list_vacancies(self) -> list[EmployerVacancy]:
        """Вернуть вакансии по убыванию времени последней синхронизации."""
        return self._repository.list_vacancies()

    @staticmethod
    def _parse_tokens(response: httpx.Response) -> tuple[str, str, int]:
        payload = response.json()
        if not isinstance(payload, dict):
            raise TypeError("token response must be an object")
        access_token = payload["access_token"]
        refresh_token = payload["refresh_token"]
        expires_in = payload["expires_in"]
        if not isinstance(access_token, str) or not access_token:
            raise ValueError("missing access token")
        if not isinstance(refresh_token, str) or not refresh_token:
            raise ValueError("missing refresh token")
        if isinstance(expires_in, bool) or not isinstance(expires_in, int) or expires_in < 0:
            raise ValueError("invalid token lifetime")
        return access_token, refresh_token, expires_in

    def _store_tokens(self, access_token: str, refresh_token: str, expires_in: int) -> None:
        now = datetime.now(UTC)
        token = self._find_token()
        if token is None:
            token = EmployerOAuthToken(
                user_id=self.user_id,
                access_token=access_token,
                refresh_token=refresh_token,
                expires_at=now + timedelta(seconds=expires_in),
                updated_at=now,
            )
        else:
            token.access_token = access_token
            token.refresh_token = refresh_token
            token.expires_at = now + timedelta(seconds=expires_in)
            token.updated_at = now
        self._repository.save_token(token)
        self._session.commit()

    async def _get_access_token(self) -> str | None:
        token = self._find_token()
        if token is None:
            self._session.commit()
            return None
        access_token = token.access_token
        expired = self._as_utc(token.expires_at) <= datetime.now(UTC)
        self._session.commit()
        if expired:
            return await self._refresh_access_token(access_token)
        return access_token

    async def _refresh_access_token(self, stale_access_token: str | None) -> str:
        token = self._repository.get_token(for_update=True)
        if token is None:
            self._session.rollback()
            raise EmployerSyncError("HH employer account is not connected")
        if stale_access_token is not None and token.access_token != stale_access_token:
            access_token = token.access_token
            self._session.commit()
            return access_token

        try:
            response = await self._client.post(
                "/token",
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": token.refresh_token,
                },
            )
            response.raise_for_status()
            access_token, refresh_token, expires_in = self._parse_tokens(response)
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
            self._session.rollback()
            raise EmployerSyncError("HH OAuth token refresh failed") from exc

        now = datetime.now(UTC)
        token.access_token = access_token
        token.refresh_token = refresh_token
        token.expires_at = now + timedelta(seconds=expires_in)
        token.updated_at = now
        self._repository.save_token(token)
        self._session.commit()
        return access_token

    @staticmethod
    def _authorization_headers(access_token: str | None) -> dict[str, str] | None:
        if access_token is None:
            return None
        return {"Authorization": f"Bearer {access_token}"}

    def _find_token(self) -> EmployerOAuthToken | None:
        return self._repository.get_token()

    @staticmethod
    def _is_token_expired(response: httpx.Response) -> bool:
        if response.status_code != 403:
            return False
        try:
            payload = response.json()
        except ValueError:
            return False
        if not isinstance(payload, dict):
            return False
        errors = payload.get("errors")
        if not isinstance(errors, list):
            return False
        for error in errors:
            if not isinstance(error, dict):
                continue
            if error.get("type") == "oauth" and error.get("value") == "token_expired":
                return True
            if error.get("oauth_error") == "token-expired":
                return True
        return False

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
