FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.11.14 /uv /uvx /bin/
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/app/.venv UV_DEFAULT_INDEX=https://pypi.org/simple
RUN apt-get update && apt-get install -y --no-install-recommends poppler-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
# 1) só dependências de terceiros, a partir do lock (camada cacheada entre builds)
COPY pyproject.toml uv.lock README.md ./
COPY src/core/pyproject.toml src/core/
COPY src/api/pyproject.toml src/api/
COPY src/extractor/pyproject.toml src/extractor/
RUN uv sync --frozen --no-dev --no-install-workspace

# 2) código do workspace (enteros na raiz, core, api, extractor) e os modelos do engine
COPY src/ ./src/
COPY models/ ./models/
RUN uv sync --frozen --no-dev
ENV PATH="/app/.venv/bin:$PATH"

WORKDIR /app/src/api
EXPOSE 8000
# Um worker: o cache do histórico e o rate limit do /demo vivem em memória do processo.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--proxy-headers", "--forwarded-allow-ips", "*"]
