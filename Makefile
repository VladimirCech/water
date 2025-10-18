SHELL := /bin/bash

.PHONY: build-dev run-api-dev stop-api-dev restart-api-dev logs-api-dev \
        lint fmt type-check check test

build-api-dev:
	cd compose && docker compose build api

run-api-dev:
	cd compose && docker compose up api db minio -d

stop-api-dev:
	cd compose && docker compose down

restart-api-dev:
	cd compose && docker compose restart api

logs-api-dev:
	cd compose && docker compose logs -f api

# Code quality targets
lint:
	cd water_api && poetry run ruff check app/

fmt:
	cd water_api && poetry run ruff format app/ && poetry run ruff check --fix app/

type-check:
	cd water_api && poetry run mypy app/

check: lint type-check
	@echo "✅ All checks passed!"

test:
	cd water_api && poetry run pytest
