"""Команды обслуживания пользователей приложения."""

import argparse
import getpass
import sys
from datetime import timedelta

from sqlmodel import Session

from fezzyvig.config.settings import get_settings
from fezzyvig.services.auth import AuthError, AuthService


def main(argv: list[str] | None = None) -> int:
    """Создать пользователя, читая пароль из аргумента или стандартного ввода."""
    parser = argparse.ArgumentParser(description="Add a user to Fezzyvig")
    parser.add_argument("email", help="User email address")
    parser.add_argument("--password", help="Password (otherwise read from stdin)")
    parser.add_argument("--first-name", help="User first name")
    parser.add_argument("--last-name", help="User last name")
    args = parser.parse_args(argv)

    if args.password is not None:
        password = args.password
    elif sys.stdin.isatty():
        password = getpass.getpass("Password: ")
    else:
        password = sys.stdin.readline().rstrip("\r\n")

    if not password:
        print("Password is required", file=sys.stderr)
        return 1

    from fezzyvig.db.database import engine

    with Session(engine) as session:
        service = AuthService(session, timedelta(days=get_settings().session_lifetime_days))
        try:
            user = service.register(args.email, password, args.first_name, args.last_name)
        except AuthError as exc:
            print(f"Could not add user: {exc}", file=sys.stderr)
            return 1

    print(f"User {user.email} created")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
