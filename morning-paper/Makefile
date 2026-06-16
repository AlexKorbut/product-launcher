.PHONY: install install-node up down test render-proto run-issue list-themes serve worker

install:
	pip install -e ".[dev]"

install-node:
	cd renderer && npm install && npx playwright install chromium

up:
	docker compose up -d postgres

down:
	docker compose down

test:
	pytest

# Track A tangible artifact: render the sample fixture into a themed PDF.
render-proto:
	python -m morning_paper.cli render-proto --theme times-classic --out issue.pdf

list-themes:
	python -m morning_paper.cli list-themes

# End-to-end issue for a user (later phases).
run-issue:
	python -m morning_paper.cli run-issue --user me --theme times-classic

# FastAPI backend (needs the `api` extra: pip install -e ".[api]").
serve:
	python -m morning_paper.cli serve

# Celery worker (needs the `worker` extra + MP_BROKER_URL; start redis via:
# docker compose --profile workers up -d redis).
worker:
	python -m morning_paper.cli worker
