# Fezzyvig

Небольшое отдельное приложение работодателя для HeadHunter. Оно подключает кабинет
через OAuth 2.0 + PKCE, синхронизирует вакансии работодателя и показывает их в web-интерфейсе.

## Запуск

```bash
cp .env.example .env
docker compose up --build
```

Перед запуском заполните в `.env` параметры OAuth-приложения HeadHunter и укажите
реальный контакт в `HH_USER_AGENT`. Callback URL приложения должен совпадать с
`HH_REDIRECT_URI`.

После запуска:

- web-интерфейс: http://localhost:9081/;
- Swagger UI: http://localhost:9081/docs;
- health check: http://localhost:9081/health.

Пара OAuth-токенов хранится в базе данных и автоматически обновляется после истечения
`access_token`. Новый одноразовый `refresh_token` сохраняется при каждой ротации. Перед
production-развёртыванием нужны шифрование токенов в хранилище, идентификация
работодателя и аудит действий.

## Локальная разработка

```bash
uv sync
source .venv/bin/activate
alembic upgrade head
uvicorn fezzyvig.main:app --reload
```

Приложение будет доступно по адресу http://127.0.0.1:8000/. Для запуска без Docker
укажите в `.env` адрес доступного с хоста PostgreSQL, например:

```dotenv
DATABASE_URL=postgresql+psycopg://fezzyvig:fezzyvig@localhost:5432/fezzyvig
```

Alembic применяет только ещё не установленные миграции. После обновления приложения
команду `alembic upgrade head` следует выполнить перед запуском.

При первом открытии создайте пользователя через форму регистрации. После входа
HH-токены и вакансии будут храниться отдельно для каждого пользователя. Сессия
передаётся в защищённой от JavaScript `HttpOnly` cookie.

Во втором терминале:

```bash
cd frontend
npm install
npm run dev
```

Проверки:

```bash
pytest
ruff check src tests
mypy src
cd frontend && npm run typecheck
```

## CI/CD

Pull request в `dev` запускает тесты, линтер и проверку типов Python, а также
сборку frontend. После слияния в `dev` те же проверки выполняются повторно и,
если они прошли, Docker-образ публикуется в GitHub Container Registry с тегами
`dev` и `sha-<commit SHA>` по адресу `ghcr.io/audrus1917/fezzyvig`.

Публикация использует встроенный `GITHUB_TOKEN` с правом `packages: write`;
дополнительные секреты не требуются. Развёртывание на сервер пока не настроено:
для него нужны адрес сервера и способ доступа.
