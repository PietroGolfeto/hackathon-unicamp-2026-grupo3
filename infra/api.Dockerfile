FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
RUN apt-get update && apt-get install -y --no-install-recommends poppler-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY src/ /app/src/
# core é obrigatório; model e extractor entram se as pastas tiverem pyproject (P1/P3).
RUN pip install -e /app/src/core -e /app/src/api \
    && for p in model extractor; do \
         if [ -f "/app/src/$p/pyproject.toml" ]; then pip install -e "/app/src/$p"; fi; \
       done

WORKDIR /app/src/api
EXPOSE 8000
# Um worker: o cache do histórico e o rate limit do /demo vivem em memória do processo.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--proxy-headers", "--forwarded-allow-ips", "*"]
