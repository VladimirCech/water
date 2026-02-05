SHELL := /bin/bash

# Directories
COMPOSE_DIR := compose
API_DIR := water_api

# Docker Compose commands
DC := cd $(COMPOSE_DIR) && docker compose
DC_EXEC := $(DC) exec -w /app api
DC_RUN := poetry run

.PHONY: build-dev run-api-dev stop-api-dev restart-api-dev logs-api-dev db-reset seed-dev \
        migrate-create migrate-up migrate-down migrate-history migrate-current migrate-stamp \
        lint fmt type-check check test run-launcher install-launcher setup demo

# =============================================================================
# 🚀 QUICK START (for new users)
# =============================================================================

setup:
	@echo "🚀 Water Game Store - Cold Start Setup"
	@echo "======================================="
	@echo ""
	@echo "Step 1/5: Building Docker images..."
	$(DC) build api
	@echo ""
	@echo "Step 2/5: Starting services (PostgreSQL, MinIO, API)..."
	$(DC) up -d db minio
	@echo "   Waiting for database to be ready..."
	@sleep 5
	$(DC) up -d api
	@echo "   Waiting for API to start..."
	@sleep 3
	@echo ""
	@echo "Step 3/5: Running database migrations..."
	$(DC_EXEC) $(DC_RUN) alembic upgrade head
	@echo ""
	@echo "Step 4/5: Seeding demo data..."
	$(DC_EXEC) $(DC_RUN) python -m app.seed
	@echo ""
	@echo "Step 5/5: Installing launcher dependencies..."
	cd water_client && poetry install
	@echo ""
	@echo "======================================="
	@echo "✅ Setup complete!"
	@echo ""
	@echo "📋 What's next:"
	@echo "   make run-launcher    # Start the launcher"
	@echo ""
	@echo "🔑 Login credentials:"
	@echo "   admin / Admin1234"
	@echo "   testuser / Test1234"
	@echo ""
	@echo "🌐 URLs:"
	@echo "   API:   http://localhost:8080/docs"
	@echo "   MinIO: http://localhost:9001 (minioadmin/minioadmin)"
	@echo "======================================="

demo: setup run-launcher

# =============================================================================
# 🐳 Docker Services
# =============================================================================

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

db-reset:
	@echo "⚠️  This will DELETE all data in the database!"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		($(DC) down -v) && \
		($(DC) up db minio -d) && \
		sleep 3 && \
		($(DC) up api -d) && \
		sleep 2 && \
		($(DC_EXEC) $(DC_RUN) alembic upgrade head) && \
		echo "✅ Database reset complete. Run 'make seed-dev' to add demo data."; \
	fi

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

# Launcher
run-launcher:
	cd water_client && poetry run python -m launcher

install-launcher:
	cd water_client && poetry install
