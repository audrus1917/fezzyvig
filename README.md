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

Создайте пользователя командой (пароль будет запрошен без отображения):

```bash
docker compose exec api fezzyvig-add-user user@example.com --first-name Иван --last-name Иванов
```

Пара OAuth-токенов хранится в базе данных и автоматически обновляется после истечения
`access_token`. Новый одноразовый `refresh_token` сохраняется при каждой ротации. Перед
production-развёртыванием нужны шифрование токенов в хранилище, идентификация
работодателя и аудит действий.

Синхронизация вакансий выполняется воркером Celery через Redis. `POST /employer/sync`
возвращает `202` и `task_id`; состояние и количество синхронизированных вакансий
доступны по `GET /employer/sync/{task_id}` только владельцу задачи.

## Локальная разработка

Слои backend: `api` принимает HTTP-запросы и возвращает схемы Pydantic,
`services` выполняет сценарии и управляет транзакциями, `repositories` содержит
запросы к БД, `models` описывает таблицы SQLAlchemy. Схема БД обновляется через Alembic.

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
CELERY_BROKER_URL=redis://localhost:6379/0
```

Alembic применяет только ещё не установленные миграции. После обновления приложения
команду `alembic upgrade head` следует выполнить перед запуском.

Для локальной фоновой синхронизации запустите Redis и воркер в отдельных терминалах:

```bash
docker compose up -d redis
celery -A fezzyvig.tasks:celery_app worker --loglevel=info
```

Форма регистрации пока скрыта. Локально пользователя можно создать командой
`fezzyvig-add-user user@example.com --first-name Иван --last-name Иванов`.
Пароль также можно передать аргументом
`--password` или через стандартный ввод:

```bash
printf '%s\n' "$NEW_USER_PASSWORD" | fezzyvig-add-user user@example.com --first-name Иван --last-name Иванов
```

Гость перенаправляется на `/login`. После входа
HH-токены и вакансии хранятся отдельно для каждого пользователя. Сессия
передаётся в защищённой от JavaScript `HttpOnly` cookie. Тексты интерфейса
настраиваются в `frontend/src/branding.ts`, цвета — в начале
`frontend/src/styles.css`.

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

Сообщения ошибок API переводятся на русский при заголовке `Accept-Language: ru`.
Без него API возвращает исходные английские сообщения. После изменения каталога
`src/fezzyvig/locale/ru/LC_MESSAGES/fezzyvig.po` обновите бинарный каталог:

```bash
msgfmt src/fezzyvig/locale/ru/LC_MESSAGES/fezzyvig.po -o src/fezzyvig/locale/ru/LC_MESSAGES/fezzyvig.mo
```

## CI/CD

Pull request в `dev` запускает тесты, линтер и проверку типов Python, а также
сборку frontend. После слияния в `dev` те же проверки выполняются повторно и,
если они прошли, Docker-образ публикуется в GitHub Container Registry с тегами
`dev` и `sha-<commit SHA>` по адресу `ghcr.io/audrus1917/fezzyvig`.

Публикация использует встроенный `GITHUB_TOKEN` с правом `packages: write`;
дополнительные секреты не требуются. Развёртывание на сервер пока не настроено:
для него нужны адрес сервера и способ доступа.
