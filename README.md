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

This starts PostgreSQL and MinIO, applies migrations, and runs backend and
frontend with hot reload. Stop application processes with `Ctrl+C`. Useful commands:

```bash
make seed  # recreate demo workspace data
make test  # run backend and frontend checks
make stop  # stop Docker services
```

For an OCR-ready backend fully inside Docker:

```bash
make production
```

This image includes Tesseract with Russian and English language data. MinIO API
is exposed at `http://localhost:9000`, its console at `http://localhost:9001`.

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

## Tenant Isolation

Tenant isolation has two independent layers:

- API queries validate the authenticated membership and scope records by
  `tenant_id`;
- PostgreSQL applies `ENABLE ROW LEVEL SECURITY` plus
  `FORCE ROW LEVEL SECURITY` to every tenant-owned business table.

API sessions switch each transaction to the restricted `cmr_app` role and set
`app.tenant_id` only after membership validation. Without that context, RLS is
default deny and tenant tables return no rows. The context is restored after
service-level commits. Migrations and maintenance scripts do not switch roles.

`0011_tenant_rls` also adds tenant-aware composite foreign keys so a row cannot
reference a company, contact, deal, document, connector account, or user
membership owned by another tenant. The local `owner@example.com` login and its
`developer-test` membership are unchanged.

When migration and API connections use different PostgreSQL login roles, grant
the API login membership in `cmr_app`; it must use `SET ROLE`, not inherit broad
migration privileges.

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

The `local` provider uses deterministic word hashes and is intended only for
offline tests. Production RAG uses a real multilingual embedding API.

1. Add a document.
2. Run search.
3. Ask a question.
4. Check the answer and citations.

Knowledge retrieval uses an explicit scope contract:

- `global`: only general workspace documents;
- `company`: only base documents of one company;
- `deal`: selected deal documents plus base documents of its company;
- `include_global`: explicit opt-in for adding general workspace documents to a
  company or deal query.

Every knowledge chunk stores filter metadata: `tenant_id`, `scope`, `company_id`, and
`deal_id`. Metadata filtering happens before similarity ranking. Scope and context are
also written to the knowledge query audit log.

For the current APIYI OpenAI-compatible provider:

```bash
EMBEDDING_PROVIDER="openai_compatible"
EMBEDDING_API_KEY="..."       # optional; falls back to LLM_API_KEY
EMBEDDING_BASE_URL=".../v1"   # optional; falls back to LLM_BASE_URL
EMBEDDING_MODEL="text-embedding-3-small"
EMBEDDING_DIMENSIONS=1536       # must match PostgreSQL vector(1536)
```

Remote provider configuration is strict: missing credentials, an unknown
provider, or an unavailable model raises an error instead of silently falling
back to local hashes. Existing documents must be reindexed after changing the
embedding model.

Apply embedding metadata migration and rebuild all existing vectors:

```bash
.venv/bin/alembic upgrade head
.venv/bin/python scripts/reindex_knowledge.py
```

Reindex is transactional: provider failure rolls back the whole operation.
Search ignores chunks whose provider, model, version, or dimensions do not
match the current embedding configuration.

Real knowledge file upload:

```text
POST /knowledge/documents/upload
multipart fields: file, title?, scope, company_id?, deal_id?
GET /knowledge/documents/{document_id}/download
```

Supported formats: text and scanned PDF, DOCX, TXT in UTF-8/UTF-16/CP1251.
Files are limited to 20 MB, PDFs to 500 pages, and extracted text to 500,000
characters. Metadata is stored in `files`; parsed chunks are embedded and
written to pgvector.

Production file storage uses any S3-compatible service. Local development uses
the bundled MinIO instance:

```bash
KNOWLEDGE_STORAGE_BACKEND=s3
S3_ENDPOINT_URL=http://localhost:9000
S3_ACCESS_KEY=cmrminio
S3_SECRET_KEY=cmrminio-dev-secret
S3_BUCKET=cmr-knowledge
S3_REGION=us-east-1
S3_USE_SSL=false
```

For AWS S3, omit `S3_ENDPOINT_URL`, enable TLS, use IAM-provided credentials,
and optionally set `S3_SERVER_SIDE_ENCRYPTION=AES256` or `aws:kms`. Existing
local files remain readable because every file records its storage backend;
moving old objects to S3 is a separate migration.

PDF pages without a text layer are rendered and recognized by Tesseract. OCR is
configured with `KNOWLEDGE_OCR_LANGUAGES=rus+eng`, DPI, per-page timeout, and an
OCR page limit. On a host run, install Tesseract plus Russian/English language
packs. The production Docker image already contains them. The extraction method
and source page count are saved on each knowledge document.

Embeddings are stored as native PostgreSQL `vector(1536)` values. Retrieval uses
exact cosine distance in SQL after tenant/company/deal and embedding identity
filters. HNSW indexing will be added when collection size justifies approximate
search. Hybrid full-text search and reranking remain later targets.

`EMBEDDING_DIMENSIONS` is a schema contract, not a runtime tuning switch. The
local deterministic provider also emits 1536-dimensional vectors. A remote
provider response with another size fails before database write. Changing the
dimension requires an Alembic migration followed by a full reindex.

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
- `POST /connectors/accounts/{account_id}/sync`
- `POST /connectors/accounts/{account_id}/csv/import`
- `GET /connectors/csv/export`
- `GET /connectors/runs`
- `POST /connectors/runs/{run_id}/retry`

Current capabilities:

- connector registry;
- connector account creation;
- real IMAP credential validation;
- incremental email sync by IMAP UID;
- MIME/header decoding and duplicate protection;
- encrypted connector credentials;
- CSV contact and lead import;
- CSV export;
- sync run history.

Email setup in UI:

1. Set a unique `SECRET_KEY` of at least 32 characters in `.env` and restart backend.
2. Open `Connectors` and select `Email (IMAP)`.
3. Enter IMAP host, port, mailbox login, app password, and folder.
4. Click `Проверить и подключить`.
5. Click `Sync now`; imported messages appear in `Inbox`.

Gmail uses `imap.gmail.com:993` and an App Password. Microsoft 365 requires OAuth
2.0; it is intentionally absent from the password form. Provider OAuth flows and a
webhook/subscription worker are separate production deployment work.

CSV columns:

```text
name,phone,email,company_name,lead_title,source
```

Placeholder connectors:

- Telegram;
- WhatsApp;
- telephony;
- calendar API;
- Bitrix24;
- amoCRM;
- 1C.

## Communication Hub

Backend endpoints:

- `GET /communication/events`
- `POST /communication/events`
- `POST /communication/ingest`
- `PATCH /communication/events/{event_id}/link`
- `POST /communication/events/{event_id}/activity`

Imported email, calls, meetings, and messenger placeholders share one
`CommunicationEvent` model. Events can be linked to company, contact, and deal and
then added to the CRM timeline as an Activity. AI summary is intentionally excluded
from this phase.

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
