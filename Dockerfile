# === Builder stage ===
FROM python:3.11-slim AS builder

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy dependency files
COPY pyproject.toml uv.lock* ./

# Install dependencies
RUN uv sync --frozen --no-dev

# === Runtime stage ===
FROM python:3.11-slim AS runtime

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Download spaCy model
RUN python -m spacy download en_core_web_sm

# Copy application code
COPY data/ data/
COPY nlp/ nlp/
COPY api/ api/
COPY db/ db/

# Copy pre-built data (if available)
# COPY data/processed/ data/processed/

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
