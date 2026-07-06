# CMR Sales App

Фаза 01: foundation.

Что уже есть:
- FastAPI backend;
- users;
- tenants;
- memberships;
- JWT login;
- tenant isolation через `X-Tenant-Id`;
- health check;
- базовое создание компании вместе с owner-пользователем.

## Локальный запуск

Установить зависимости:

```bash
cd cmr_sales_app
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

Альтернатива для editable-install:

```bash
pip install -e ".[dev]"
```

Запустить:

```bash
uvicorn app.main:app --reload
```

Документация API:

```text
http://localhost:8000/docs
```

## Frontend

В отдельном терминале:

```bash
cd cmr_sales_app/frontend
npm install
npm run dev
```

Открыть:

```text
http://localhost:5173
```

Frontend MVP содержит:

- регистрацию компании;
- вход;
- Vue Router routes: `/login`, `/dashboard`, `/companies`, `/companies/:id`, `/leads`, `/deals`, `/timeline`, `/tasks`, `/knowledge`, `/agent`, `/connectors`, `/templates`, `/production`, `/settings`;
- dashboard с метриками;
- company workspace;
- создание контактов и лидов;
- список лидов;
- создание воронки;
- создание сделок;
- kanban по этапам;
- перенос сделки между этапами;
- единая activity timeline;
- создание и закрытие задач;
- база знаний и RAG-вопросы;
- AI агент с подтверждаемыми действиями;
- коннекторы и CSV import/export;
- шаблоны внедрения под типы компаний;
- production overview, audit, flags, limits, export;
- настройки tenant;
- заметки к лидам и сделкам.

## Переменные

По умолчанию используется PostgreSQL.

Запуск БД:

```bash
docker compose up -d postgres
```

Миграции:

```bash
source .venv/bin/activate
alembic upgrade head
```

Подключение:

```bash
export DATABASE_URL="postgresql+psycopg://cmr:cmr@localhost:5432/cmr"
```

SQLite больше не является целевой dev-базой. Можно использовать только для быстрых локальных тестов через явный `DATABASE_URL=sqlite:///...`.

Обязательно поменять в production:

```bash
export SECRET_KEY="long-random-secret"
```

## Демо-данные для проверки интерфейса

После миграций можно заполнить базу тестовыми данными:

```bash
python scripts/seed_demo.py
```

Демо-вход:

- email: `demo@cmr.local`
- password: `password123`

Скрипт пересоздает только demo-tenant `demo-sales-ai`, поэтому его можно запускать повторно во время тестирования.

## Быстрый сценарий

1. `POST /auth/register-company`
2. `POST /auth/login`
3. Взять `access_token`.
4. В запросы добавить:
   - `Authorization: Bearer <token>`
   - `X-Tenant-Id: <tenant_id>`
5. Проверить `GET /me`.

## Фаза 02: CRM core

После авторизации доступны endpoints:

- `POST /sales/contacts`
- `GET /sales/contacts`
- `POST /sales/leads`
- `GET /sales/leads`
- `GET /sales/leads/{lead_id}`
- `POST /sales/pipelines`
- `GET /sales/pipelines`
- `POST /sales/deals`
- `GET /sales/deals`
- `PATCH /sales/deals/{deal_id}/move`
- `POST /sales/tasks`
- `GET /sales/tasks`
- `PATCH /sales/tasks/{task_id}/done`
- `POST /sales/notes`
- `GET /sales/notes`

Минимальный порядок проверки:

1. Создать pipeline.
2. Взять `stage_id` первого этапа.
3. Создать contact.
4. Создать lead с `contact_id`.
5. Создать deal с `lead_id` и `stage_id`.
6. Создать task по сделке.
7. Создать note по lead или deal.

## Фаза 04: RAG

Backend endpoints:

- `POST /knowledge/documents`
- `GET /knowledge/documents`
- `GET /knowledge/documents/{document_id}`
- `POST /knowledge/search`
- `POST /knowledge/ask`

Frontend:

```text
http://localhost:5173/knowledge
```

Локально RAG работает без внешнего API через deterministic local embeddings. Это удобно для проверки потока:

1. Добавить документ.
2. Выполнить поиск.
3. Задать вопрос.
4. Проверить ответ и источники.

Для OpenAI embeddings:

```bash
export OPENAI_API_KEY="..."
export EMBEDDING_PROVIDER="openai"
export EMBEDDING_MODEL="text-embedding-3-small"
```

Текущий MVP хранит embeddings как JSON, чтобы одинаково работать на SQLite и PostgreSQL. Production-следующий шаг: `pgvector`, hybrid search, reranker.

## Фаза 05: AI agent

Backend endpoints:

- `POST /ai-agent/chat`
- `GET /ai-agent/history`
- `GET /ai-agent/actions`
- `POST /ai-agent/actions/{action_id}/confirm`
- `POST /ai-agent/actions/{action_id}/reject`

Frontend:

```text
http://localhost:5173/agent
```

Что умеет MVP:

- отвечает по базе знаний через RAG;
- дает сводку по CRM;
- предлагает создать задачу;
- предлагает перенести сделку на этап;
- не меняет CRM без подтверждения пользователя.

Примеры сообщений:

```text
Дай сводку по CRM
Создай задачу позвонить клиенту
Перенеси сделку Первая сделка на этап КП
Что делать после новой заявки?
```

## Фаза 06: Connectors

Backend endpoints:

- `GET /connectors/definitions`
- `POST /connectors/accounts`
- `GET /connectors/accounts`
- `POST /connectors/accounts/{account_id}/csv/import`
- `GET /connectors/csv/export`
- `GET /connectors/runs`

Frontend:

```text
http://localhost:5173/connectors
```

Что умеет MVP:

- показывает реестр коннекторов;
- подключает connector account;
- импортирует контакты и лиды из CSV;
- экспортирует лиды в CSV;
- хранит историю синхронизаций.

CSV columns:

```text
name,phone,email,company_name,lead_title,source
```

Planned connectors:

- email;
- Telegram;
- Bitrix24;
- amoCRM;
- 1C.

## Фаза 07: Company templates

Backend endpoints:

- `GET /templates`
- `POST /templates/apply`
- `GET /templates/applied`

Frontend:

```text
http://localhost:5173/templates
```

Что умеет MVP:

- показывает отраслевые шаблоны;
- применяет шаблон к текущей компании;
- создает воронку и этапы;
- добавляет playbook в базу знаний;
- хранит историю примененных шаблонов.

Доступные шаблоны:

- B2B услуги;
- оптовая торговля;
- недвижимость;
- онлайн-образование;
- производство.

## Фаза 08: Production foundation

Backend endpoints:

- `GET /health/ready`
- `GET /production/overview`
- `GET /production/audit`
- `POST /production/audit`
- `GET /production/flags`
- `POST /production/flags`
- `PATCH /production/flags/{flag_id}`
- `GET /production/plan`
- `PUT /production/plan`
- `GET /production/export`

Frontend:

```text
http://localhost:5173/production
```

Что умеет MVP:

- показывает counts по tenant;
- хранит тариф и лимиты;
- управляет feature flags;
- показывает audit log;
- делает JSON export tenant data;
- проверяет readiness API.

Что еще нужно перед настоящим production:

- Alembic migrations;
- PostgreSQL + pgvector;
- полноценный RBAC;
- rate limits;
- background jobs;
- object storage;
- monitoring;
- error tracking;
- backups;
- CI/CD.

## Phase 09: Activity Timeline

Backend endpoints:

- `GET /activities`
- `POST /activities`

Frontend:

```text
http://localhost:5173/timeline
```

Что умеет MVP:

- хранит единую ленту действий;
- поддерживает типы `EMAIL`, `CALL`, `MEETING`, `TASK`, `NOTE`, `DEAL_STAGE_CHANGED`, `FILE`, `COMMENT`, `SYSTEM`, `AI_ACTION`;
- автоматически пишет activity при создании контакта, лида, сделки, задачи, заметки;
- автоматически пишет activity при переносе сделки;
- автоматически пишет activity при подтвержденном AI-действии;
- позволяет вручную добавить activity из UI.

Важно:

- `company_id` уже есть в модели, но пока nullable;
- отдельная сущность Company будет добавлена следующим слоем.

## Phase 10: Company Workspace

Backend endpoints:

- `POST /sales/companies`
- `GET /sales/companies`
- `GET /sales/companies/{company_id}`

Frontend:

```text
http://localhost:5173/companies
http://localhost:5173/companies/{company_id}
```

Что умеет MVP:

- компания стала отдельной сущностью;
- есть список компаний;
- есть карточка компании;
- карточка показывает Overview;
- Timeline;
- Contacts;
- Deals;
- Tasks;
- Knowledge placeholder;
- Files placeholder;
- AI Summary;
- AI Insights;
- History placeholder.

Важно:

- текущая связь контактов с компанией идет через `Contact.company_name == Company.name`;
- следующий слой: добавить явный `company_id` в contacts/leads/deals/tasks через миграции.
