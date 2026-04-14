.PHONY: setup dev dev-frontend test test-all test-cov lint format check seed ingest-full clean

# === Setup ===
setup:
	uv sync --dev
	uv run python -m spacy download en_core_web_sm
	uv run pre-commit install
	@if not exist .env copy .env.example .env
	@echo Setup complete. Edit .env with your API keys.

# === Development ===
dev:
	uv run uvicorn api.main:app --reload --port 8000

dev-frontend:
	cd frontend && npm install && npm run dev

# === Data ===
seed:
	uv run python scripts/seed_data.py --sample-size 500

ingest-fr:
	uv run python -m data.ingest.federal_register --since 2020-01-01

ingest-comments:
	uv run python -m data.ingest.regulations_gov --docket FCC-17-108

embed:
	uv run python -m nlp.embed --batch-size 256

cluster:
	uv run python -m nlp.cluster

dedup:
	uv run python -m nlp.dedup --threshold 0.8

citations:
	uv run python -m nlp.citations

summarize:
	uv run python -m nlp.summarize

ingest-full: ingest-fr ingest-comments embed cluster dedup citations summarize
	@echo Full pipeline complete.

# === Quality ===
lint:
	uv run ruff check .
	uv run mypy data/ nlp/ api/ db/

format:
	uv run ruff format .
	uv run ruff check --fix .

test:
	uv run pytest -m "not slow and not integration" --tb=short -q

test-all:
	uv run pytest --tb=short

test-cov:
	uv run pytest --cov-report=html
	@echo Open htmlcov/index.html in browser

check: lint test
	@echo All checks passed.

# === Deploy ===
build:
	docker build -t regscope .

# === Clean ===
clean:
	@if exist __pycache__ rmdir /s /q __pycache__
	@if exist .pytest_cache rmdir /s /q .pytest_cache
	@if exist htmlcov rmdir /s /q htmlcov
	@if exist .mypy_cache rmdir /s /q .mypy_cache
	@if exist .ruff_cache rmdir /s /q .ruff_cache
