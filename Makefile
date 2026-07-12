.DEFAULT_GOAL := help

PYTHON := .venv/bin/python
ALEMBIC := .venv/bin/alembic

.PHONY: help check db db-ready migrate dev seed test stop

help:
	@echo "CMR Sales App"
	@echo "  make dev   - start database, backend, and frontend"
	@echo "  make seed  - recreate demo workspace data"
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

migrate: check db-ready
	$(ALEMBIC) upgrade head

dev:
	bash scripts/dev.sh

seed: check db-ready migrate
	$(PYTHON) scripts/seed_demo.py

test: check
	$(PYTHON) -m compileall -q app scripts
	npm --prefix frontend run build

stop:
	docker compose down
