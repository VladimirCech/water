SHELL := /bin/bash

# Directories
COMPOSE_DIR := compose
API_DIR := water_api

# Docker Compose commands
DC := cd $(COMPOSE_DIR) && docker compose
DC_EXEC := $(DC) exec -w /app api
DC_RUN := poetry run

.PHONY: build-dev run-api-dev stop-api-dev restart-api-dev logs-api-dev seed-dev \
        migrate-create migrate-up migrate-down migrate-history migrate-current migrate-stamp \
        lint fmt type-check check test

# Docker services
build-api-dev:
	$(DC) build api

run-api-dev:
	$(DC) up api db minio -d

stop-api-dev:
	$(DC) down

restart-api-dev:
	$(DC) restart api

logs-api-dev:
	$(DC) logs -f api

# Database operations
seed-dev:
	$(DC_EXEC) $(DC_RUN) python -m app.seed

# Database migrations
migrate-create:
	@read -p "Migration name: " name; \
	$(DC_EXEC) $(DC_RUN) alembic revision --autogenerate -m "$$name"

migrate-up:
	$(DC_EXEC) $(DC_RUN) alembic upgrade head

migrate-down:
	$(DC_EXEC) $(DC_RUN) alembic downgrade -1

migrate-history:
	$(DC_EXEC) $(DC_RUN) alembic history

migrate-current:
	$(DC_EXEC) $(DC_RUN) alembic current

migrate-stamp:
	$(DC_EXEC) $(DC_RUN) alembic stamp head

# Code quality targets
lint:
	cd $(API_DIR) && poetry run ruff check app/

fmt:
	cd $(API_DIR) && poetry run ruff format app/ && poetry run ruff check --fix app/

type-check:
	cd $(API_DIR) && poetry run mypy app/

check: lint type-check
	@echo "✅ All checks passed!"

test:
	cd $(API_DIR) && poetry run pytest
