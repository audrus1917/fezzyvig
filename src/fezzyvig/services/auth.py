"""Password authentication and server-side session management."""

import base64
import hashlib
import hmac
import re
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from fezzyvig.models.user import User, UserSession

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class AuthError(ValueError):
    """An authentication request cannot be completed."""


class AuthService:
    """Create users and manage opaque browser sessions."""

    def __init__(self, session: Session, session_lifetime: timedelta) -> None:
        self._session = session
        self._session_lifetime = session_lifetime

    def register(self, email: str, password: str, first_name: str, last_name: str) -> User:
        """Создать пользователя, нормализовать данные и хешировать пароль."""
        normalized_email = self._normalize_email(email)
        self._validate_password(password)
        first_name = self._normalize_name(first_name)
        last_name = self._normalize_name(last_name)
        user = User(
            email=normalized_email,
            first_name=first_name,
            last_name=last_name,
            password_hash=self._hash_password(password),
        )
        self._session.add(user)
        try:
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            raise AuthError("A user with this email already exists") from exc
        self._session.refresh(user)
        return user

    def authenticate(self, email: str, password: str) -> User:
        """Return a user when the supplied credentials are valid."""
        normalized_email = self._normalize_email(email)
        user = self._session.exec(select(User).where(User.email == normalized_email)).first()
        if user is None or not self._verify_password(password, user.password_hash):
            raise AuthError("Invalid email or password")
        return user

    def create_session(self, user: User) -> str:
        """Create and persist a new opaque session token."""
        if user.id is None:
            raise AuthError("User must be persisted before creating a session")
        token = secrets.token_urlsafe(32)
        self._session.add(
            UserSession(
                token_hash=self._hash_token(token),
                user_id=user.id,
                expires_at=datetime.now(UTC) + self._session_lifetime,
            )
        )
        self._session.commit()
        return token

    def get_user(self, token: str | None) -> User | None:
        """Resolve an unexpired session token to its user."""
        if not token:
            return None
        user_session = self._session.get(UserSession, self._hash_token(token))
        if user_session is None:
            return None
        if self._as_utc(user_session.expires_at) <= datetime.now(UTC):
            self._session.delete(user_session)
            self._session.commit()
            return None
        return self._session.get(User, user_session.user_id)

    def delete_session(self, token: str | None) -> None:
        """Revoke a session token if it exists."""
        if not token:
            return
        user_session = self._session.get(UserSession, self._hash_token(token))
        if user_session is not None:
            self._session.delete(user_session)
            self._session.commit()

    @staticmethod
    def _normalize_email(email: str) -> str:
        normalized = email.strip().casefold()
        if len(normalized) > 320 or not EMAIL_PATTERN.fullmatch(normalized):
            raise AuthError("Enter a valid email address")
        return normalized

    @staticmethod
    def _validate_password(password: str) -> None:
        if len(password) < 8:
            raise AuthError("Password must contain at least 8 characters")
        if len(password) > 256:
            raise AuthError("Password is too long")

    @staticmethod
    def _normalize_name(name: str) -> str:
        """Убрать пробелы по краям и проверить длину имени."""
        normalized = name.strip()
        if not normalized or len(normalized) > 100:
            raise AuthError("Enter a name between 1 and 100 characters")
        return normalized

    @staticmethod
    def _hash_password(password: str) -> str:
        salt = secrets.token_bytes(16)
        digest = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1, dklen=64)
        return "scrypt$16384$8$1$" + "$".join(
            base64.urlsafe_b64encode(value).decode() for value in (salt, digest)
        )

    @staticmethod
    def _verify_password(password: str, encoded: str) -> bool:
        try:
            algorithm, n, r, p, salt_encoded, digest_encoded = encoded.split("$")
            if algorithm != "scrypt":
                return False
            salt = base64.urlsafe_b64decode(salt_encoded)
            expected = base64.urlsafe_b64decode(digest_encoded)
            actual = hashlib.scrypt(
                password.encode(), salt=salt, n=int(n), r=int(r), p=int(p), dklen=len(expected)
            )
        except (ValueError, TypeError):
            return False
        return hmac.compare_digest(actual, expected)

    @staticmethod
    def _hash_token(token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
