"""Запросы к токенам и вакансиям работодателя."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from fezzyvig.models.oauth_token import EmployerOAuthToken
from fezzyvig.models.vacancy import EmployerVacancy


class EmployerRepository:
    """Хранить токены и вакансии отдельного пользователя."""

    def __init__(self, session: Session, user_id: int) -> None:
        self.session = session
        self.user_id = user_id

    def get_token(self, *, for_update: bool = False) -> EmployerOAuthToken | None:
        statement = select(EmployerOAuthToken).where(
            EmployerOAuthToken.user_id == self.user_id,
            EmployerOAuthToken.provider == "hh",
        )
        if for_update:
            statement = statement.with_for_update()
        return self.session.scalars(statement).first()

    def save_token(self, token: EmployerOAuthToken) -> None:
        self.session.add(token)

    def get_vacancy(self, external_id: str) -> EmployerVacancy | None:
        return self.session.scalars(
            select(EmployerVacancy).where(
                EmployerVacancy.user_id == self.user_id,
                EmployerVacancy.source == "hh",
                EmployerVacancy.external_id == external_id,
            )
        ).first()

    def list_vacancies(self) -> list[EmployerVacancy]:
        return list(
            self.session.scalars(
                select(EmployerVacancy)
                .where(EmployerVacancy.user_id == self.user_id)
                .order_by(EmployerVacancy.synced_at.desc())
            ).all()
        )

    def save_vacancy(self, vacancy: EmployerVacancy) -> None:
        self.session.add(vacancy)
