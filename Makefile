# ==============================================================================
# Quantum Flow Technologies — PQC Platform Makefile
# Standard development, testing, and lifecycle commands
# ==============================================================================

.PHONY: help install lint format format-check typecheck test test-backend test-frontend \
        dev-api dev-worker dev-web docker-up docker-down docker-build migrate clean

.DEFAULT_GOAL := help

PYTHON ?= python
NPM ?= npm

help: ## Show this help message
	@echo "Quantum Flow Technologies — Engineering Foundation (Sprint 0)"
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-18s %s\n", $$1, $$2}'

install: ## Install backend and frontend dependencies
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install .
	$(NPM) install

lint: ## Run backend (Ruff) and frontend (ESLint) linters
	$(PYTHON) -m ruff check .
	$(NPM) run lint:web

format: ## Format backend code with Ruff
	$(PYTHON) -m ruff format .

format-check: ## Check code formatting without applying modifications
	$(PYTHON) -m ruff format --check .

typecheck: ## Run static type analysis (mypy + tsc)
	$(PYTHON) -m mypy services packages tests
	$(NPM) run typecheck:web

test: test-backend test-frontend ## Run all test suites (backend + frontend)

test-backend: ## Run Python backend tests
	$(PYTHON) -m pytest -v

test-frontend: ## Run React frontend tests
	$(NPM) run test:web

dev-api: ## Start FastAPI backend development server
	$(PYTHON) -m uvicorn services.api.app.main:app --reload --host 127.0.0.1 --port 8000

dev-worker: ## Start asynchronous background worker daemon
	$(PYTHON) -m services.worker.app.worker

dev-web: ## Start React frontend development server (Vite)
	$(NPM) run dev:web

docker-up: ## Start Docker Compose infrastructure services (PostgreSQL + Redis)
	docker compose up -d postgres redis

docker-down: ## Stop Docker Compose infrastructure services
	docker compose down

docker-build: ## Build all Docker container images
	docker compose build

migrate: ## Run Alembic database migrations
	$(PYTHON) -m alembic upgrade head

clean: ## Clean Python cache files, test artifacts, and build outputs
	rm -rf .pytest_cache .mypy_cache .ruff_cache apps/web/dist apps/web/node_modules/.vite
	find . -type d -name "__pycache__" -exec rm -rf {} +

