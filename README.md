# CMR Sales App

AI-first CRM platform for sales teams.

The system is built around the company workspace: companies, activity timeline,
deals, tasks, knowledge, RAG, AI agent actions, connectors, templates, analytics,
and tenant administration.

## Stack

- Backend: FastAPI, SQLAlchemy, Alembic
- Database: PostgreSQL
- Frontend: Vue 3, Vue Router, Vite
- Auth: JWT
- Multitenancy: `X-Tenant-Id`

## Local Setup

### Quick start

After installing backend and frontend dependencies once:

```bash
make dev
```

This starts PostgreSQL, applies migrations, and runs backend and frontend with
hot reload. Stop application processes with `Ctrl+C`. Useful commands:

```bash
make seed  # recreate demo workspace data
make test  # run backend and frontend checks
make stop  # stop Docker services
```

The application reads provider settings and secrets from `.env` in the project
root. If `.env` is absent, configured application defaults are used.

Install backend dependencies:

```bash
cd cmr_sales_app
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

Alternative editable install:

```bash
pip install -e ".[dev]"
```

Start PostgreSQL:

```bash
docker compose up -d postgres
```

Run migrations:

```bash
alembic upgrade head
```

Create/update developer access for local testing:

```bash
python scripts/dev_access.py
```

Developer login:

- email: `owner@example.com`
- password: `password123`

Start backend:

```bash
uvicorn app.main:app --reload
```

API docs:

```text
http://localhost:8000/docs
```

## Frontend

In another terminal:

```bash
cd cmr_sales_app/frontend
npm install
npm run dev
```

Open:

```text
http://localhost:5173
```

Current workspace navigation:

- Home
- Companies
- Deals
- Tasks
- Inbox
- Knowledge
- Analytics
- Settings

## Environment

Default local database URL:

```bash
export DATABASE_URL="postgresql+psycopg://cmr:cmr@localhost:5432/cmr"
```

SQLite is no longer the target development database. It can still be used only
for quick isolated tests with an explicit `DATABASE_URL=sqlite:///...`.

Change this before production:

```bash
export SECRET_KEY="long-random-secret"
```

## Demo Data

After migrations, seed the database with demo data for UI testing:

```bash
python scripts/seed_demo.py
```

Demo login:

- email: `demo@cmrsales.app`
- password: `password123`

The seed script recreates only the demo tenant `demo-sales-ai`, so it can be
run repeatedly during interface testing.

## API Quick Check

1. `POST /auth/register-company`
2. `POST /auth/login`
3. Copy `access_token`.
4. Add headers to requests:
   - `Authorization: Bearer <token>`
   - `X-Tenant-Id: <tenant_id>`
5. Verify `GET /me`.

## CRM Core

Backend endpoints:

- `POST /sales/companies`
- `GET /sales/companies`
- `GET /sales/companies/{company_id}`
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

Minimal test flow:

1. Create a company.
2. Create a pipeline.
3. Take the first `stage_id`.
4. Create a contact.
5. Create a lead with `contact_id`.
6. Create a deal with `lead_id` and `stage_id`.
7. Create a task for the deal.
8. Create a note for the lead or deal.

## Activity Timeline

Backend endpoints:

- `GET /activities`
- `POST /activities`

The timeline stores a unified activity feed across companies, contacts, deals,
tasks, notes, system events, and AI actions.

Supported activity types include:

- `EMAIL`
- `CALL`
- `MEETING`
- `TASK`
- `NOTE`
- `DEAL_STAGE_CHANGED`
- `FILE`
- `COMMENT`
- `SYSTEM`
- `AI_ACTION`
- `AI_SUMMARY_UPDATED`

## Company Workspace

Company is the main CRM object.

The company card includes:

- Overview
- Timeline
- Contacts
- Deals
- Tasks
- Files
- Knowledge
- AI Summary
- AI Insights
- Change History
- AI Assistant

Frontend:

```text
http://localhost:5173/companies
http://localhost:5173/companies/{company_id}
```

## RAG

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

Local RAG works without external APIs through deterministic local embeddings.
This is useful for checking the full product flow:

1. Add a document.
2. Run search.
3. Ask a question.
4. Check the answer and citations.

For OpenAI embeddings:

```bash
export OPENAI_API_KEY="..."
export EMBEDDING_PROVIDER="openai"
export EMBEDDING_MODEL="text-embedding-3-small"
```

The current implementation stores embeddings as JSON for portability. The
production target is PostgreSQL with `pgvector`, hybrid search, and reranking.

## Analytics & Forecast

Backend endpoint:

```text
GET /analytics/overview?forecast_days=90&stuck_days=14&activity_days=30
```

Tenant-scoped analytics includes:

- pipeline forecast and weighted revenue;
- conversion by pipeline stage;
- stuck deals based on last stage movement;
- task SLA and per-manager SLA;
- manager activity and owned pipeline;
- company health signals;
- AI risk map and revenue at risk.

Frontend:

```text
http://localhost:5173/analytics
```

## AI Agent

Backend endpoints:

- `POST /ai-agent/chat`
- `GET /ai-agent/history`
- `GET /ai-agent/actions`
- `POST /ai-agent/actions/{action_id}/confirm`
- `POST /ai-agent/actions/{action_id}/reject`

The AI agent is not a standalone workspace tab. It is embedded into daily work,
company cards, deal context, and knowledge workflows.

Current capabilities:

- answers with RAG context;
- summarizes CRM state;
- proposes task creation;
- proposes deal stage changes;
- does not mutate CRM data without user confirmation.

Example prompts:

```text
Give me a CRM summary
Create a task to call the client
Move the deal to Proposal
What should I do after a new inbound lead?
```

## Connectors

Backend endpoints:

- `GET /connectors/definitions`
- `POST /connectors/accounts`
- `GET /connectors/accounts`
- `POST /connectors/accounts/{account_id}/csv/import`
- `GET /connectors/csv/export`
- `GET /connectors/runs`

Current capabilities:

- connector registry;
- connector account creation;
- CSV contact and lead import;
- CSV export;
- sync run history.

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

## Company Templates

Backend endpoints:

- `GET /templates`
- `POST /templates/apply`
- `GET /templates/applied`

Current capabilities:

- industry template registry;
- template application to the current tenant;
- pipeline and stage creation;
- playbook creation in the knowledge base;
- applied template history.

Available templates:

- B2B services;
- wholesale trade;
- real estate;
- online education;
- manufacturing.

## Production Foundation

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

Current capabilities:

- tenant-level counts;
- plan and limit storage;
- feature flag management;
- audit log;
- JSON tenant data export;
- readiness API.

Before real production:

- enable `pgvector`;
- add full RBAC;
- add rate limits;
- add background jobs;
- add object storage;
- add monitoring;
- add error tracking;
- add backups;
- add CI/CD.
