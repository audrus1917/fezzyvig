"""Запросы к пользователям и браузерным сессиям."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from fezzyvig.models.user import User, UserSession


class AuthRepository:
    """Хранить пользователей и их сессии."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def add_user(self, user: User) -> None:
        self.session.add(user)

    def get_user_by_email(self, email: str) -> User | None:
        return self.session.scalars(select(User).where(User.email == email)).first()

    def get_user(self, user_id: int) -> User | None:
        return self.session.get(User, user_id)

    def add_session(self, user_session: UserSession) -> None:
        self.session.add(user_session)

    def get_session(self, token_hash: str) -> UserSession | None:
        return self.session.get(UserSession, token_hash)

    def delete_session(self, user_session: UserSession) -> None:
        self.session.delete(user_session)
