.DEFAULT_GOAL := help

PYTHON := .venv/bin/python
ALEMBIC := .venv/bin/alembic

.PHONY: help check db db-ready infra infra-ready migrate dev production seed automation-run integrations-run test stop

help:
	@echo "CRM Sales App"
	@echo "  make dev   - start database, backend, and frontend"
	@echo "  make production - build and start the full production stack"
	@echo "  make seed  - recreate demo workspace data"
	@echo "  make automation-run - process scheduled CRM automations once"
	@echo "  make integrations-run - process integration jobs once"
	@echo "  make test  - run backend and frontend checks"
	@echo "  make stop  - stop Docker services"

check:
	@test -x "$(PYTHON)" || (echo "Missing .venv. Create it and install requirements-dev.txt" && exit 1)
	@test -d frontend/node_modules || (echo "Missing frontend/node_modules. Run: cd frontend && npm install" && exit 1)
	@test -f .env || echo "Note: .env not found; application defaults will be used"

db:
	@docker info >/dev/null 2>&1 || (echo "Docker is not running. Start Docker Desktop and retry." && exit 1)
	docker compose up -d postgres

db-ready:
	@docker info >/dev/null 2>&1 || (echo "Docker is not running. Start Docker Desktop and retry." && exit 1)
	docker compose up -d --wait postgres

infra:
	@docker info >/dev/null 2>&1 || (echo "Docker is not running. Start Docker Desktop and retry." && exit 1)
	docker compose up -d postgres minio

infra-ready:
	@docker info >/dev/null 2>&1 || (echo "Docker is not running. Start Docker Desktop and retry." && exit 1)
	docker compose up -d --wait postgres minio

migrate: check db-ready
	$(ALEMBIC) upgrade head

dev:
	bash scripts/dev.sh

production:
	@docker info >/dev/null 2>&1 || (echo "Docker is not running. Start Docker Desktop and retry." && exit 1)
	docker compose --profile production up -d --build --wait \
		postgres minio backend frontend integration-worker automation-scheduler

seed: check db-ready migrate
	$(PYTHON) scripts/seed_demo.py

automation-run: check db-ready migrate
	$(PYTHON) scripts/run_automations.py

integrations-run: check db-ready migrate
	$(PYTHON) scripts/run_integration_worker.py --once

test: check
	bash scripts/quality_gate.sh

stop:
	docker compose down
