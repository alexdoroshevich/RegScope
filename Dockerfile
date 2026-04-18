# === Frontend build stage ===
FROM node:20-slim AS frontend

WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --ignore-scripts
COPY frontend/ ./
RUN npm run build

# === Python builder stage ===
FROM python:3.13-slim AS builder

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY pyproject.toml uv.lock* ./

RUN uv sync --frozen --no-dev

# === Runtime stage ===
FROM python:3.13-slim AS runtime

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

RUN python -m spacy download en_core_web_sm

COPY data/ data/
COPY nlp/ nlp/
COPY api/ api/
COPY db/ db/
COPY scripts/ scripts/

COPY --from=frontend /app/frontend/dist frontend/dist

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
