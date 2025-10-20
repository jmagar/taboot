# Makefile Reference

Targets you can automate in `Makefile` or `taskfile.yml`.

```make
.PHONY: help
help:
	@grep -E '^[a-zA-Z_-]+:.*?## ' Makefile | sort | awk -F':|##' '{printf "\033[36m%-28s\033[0m %s\n", $$1, $$3}'

setup: ## Create venv, install deps
	python -m venv .venv && . .venv/bin/activate && pip install -U pip && pip install -e .[dev]

lint: ## Ruff + codespell
	ruff check . && codespell

typecheck: ## mypy/pyright
	pyright

test: ## Run unit tests
	pytest -q

e2e: ## Spin up stack and run smoke
	docker compose up -d && python scripts/smoke.py

openapi: ## Validate and bundle OpenAPI
	npx @redocly/cli lint apps/api/openapi.yaml

clients: ## Generate TS/Python clients
	npx openapi-typescript apps/api/openapi.yaml -o packages/clients/ts/index.ts
	openapi-python-client generate --path apps/api/openapi.yaml --output packages/clients/python

run-api: ## Run FastAPI with reload
	uvicorn apps.api.main:app --reload --port 8000

format: ## Format Python
	ruff format .

compose-up: ## Bring up services
	docker compose up -d

compose-down: ## Bring down services
	docker compose down -v

```
