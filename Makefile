.DEFAULT_GOAL := help
BASE ?= origin/main
HEAD ?= HEAD
VENV := .venv
PY := $(if $(wildcard $(VENV)/bin/python),$(VENV)/bin/python,python3)
UV := $(shell command -v uv 2>/dev/null)
COMPOSE := docker compose -f infra/compose.yml --project-directory .
COMPOSE_LOCAL := $(COMPOSE) -f infra/compose.local.yml
CLI := PYTHONPATH=src/api $(PY) -m app.cli
# testes da API sempre num banco próprio: nunca o DATABASE_URL do .env (drop_all!)
TEST_DATABASE_URL ?= postgresql+psycopg://enter:enter@localhost:5432/enter_test
-include .env
export

help: ## lista os alvos disponíveis
	@grep -hE '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

# ---------------------------------------------------------------- qualidade

hooks: ## instala os hooks de git deste clone (pre-commit e commit-msg)
	git config core.hooksPath scripts/hooks
	@echo "hooks instalados em scripts/hooks (desfazer: git config --unset core.hooksPath)"

check: check-secrets check-memory-bank check-commits lint test ## roda tudo que a CI roda

check-commits: ## valida mensagem e tamanho dos commits em BASE..HEAD
	scripts/check_commits.sh $(BASE) $(HEAD)

check-memory-bank: ## exige memory-bank atualizado nos commits de código em BASE..HEAD
	scripts/check_memory_bank.sh $(BASE) $(HEAD)

check-secrets: ## bloqueia segredos e dados versionados
	scripts/check_secrets.sh

lint: ## ruff em core e api; tsc no web
	$(PY) -m ruff check src/core src/api
	@if [ -f src/web/package.json ]; then echo "→ web (tsc)"; cd src/web && npm run lint --if-present; fi

test: ## testes dos componentes que existirem (core, api com Postgres, web build)
	@if [ -f src/core/pyproject.toml ]; then echo "→ core"; $(PY) -m pytest -q src/core; fi
	@if [ -f src/api/pyproject.toml ]; then echo "→ api"; DATABASE_URL=$(TEST_DATABASE_URL) $(PY) -m pytest -q src/api; fi
	@if [ -f src/web/package.json ]; then echo "→ web"; cd src/web && npm run build; fi
	@echo "✓ testes ok"

# ---------------------------------------------------------------- ambiente local

install: ## cria .venv (Python 3.12) com core+api e instala o web
	@if [ -n "$(UV)" ]; then uv venv -q -p 3.12 $(VENV); uv pip install -q --python $(VENV)/bin/python -e src/core -e "src/api[test]"; \
	else python3 -m venv $(VENV) && $(VENV)/bin/pip install -q -e src/core -e "src/api[test]"; fi
	@for p in model extractor; do if [ -f src/$$p/pyproject.toml ]; then $(VENV)/bin/pip install -q -e src/$$p; fi; done
	cd src/web && npm install --no-audit --no-fund
	@echo "✓ pronto: make up (docker) ou make dev-api + make dev-web"

up: ## sobe db, api e caddy em http://localhost:8080 (sem TLS)
	$(COMPOSE_LOCAL) up -d --build

up-prod: ## sobe com TLS automático no DOMAIN do .env (VPS)
	$(COMPOSE) up -d --build

down: ## derruba os containers (mantém volumes)
	$(COMPOSE_LOCAL) down

logs: ## acompanha logs da api e do caddy
	$(COMPOSE_LOCAL) logs -f --tail=100 api caddy

psql: ## abre psql no Postgres do compose
	$(COMPOSE_LOCAL) exec db psql -U $${POSTGRES_USER:-enter} $${POSTGRES_DB:-enter}

dev-api: ## API com reload em :8000 (usa .env e o Postgres de `make up` ou local)
	$(PY) -m uvicorn --app-dir src/api app.main:app --reload --port 8000

dev-web: ## Vite em :5173 com proxy de /api para :8000
	cd src/web && npm run dev

# ---------------------------------------------------------------- jobs de carga (rodam onde estiver o DATABASE_URL)

seed: ## escritórios, usuários e política v1 (idempotente)
	$(CLI) seed

historico: ## carrega os 2 CSVs da Enter de data/ e avisa a API
	$(CLI) load-historico

ingest: ## lê data/exemplos/<numero>/ (autos e subsídios) para processos
	$(CLI) ingest

seed-demo: ## processos sintéticos + decisões simuladas (idempotente)
	$(CLI) seed-demo

reset-demo: ## apaga decisões, eventos e recomendações; mantém processos e políticas
	$(CLI) reset-demo

reset: ## recria o banco LOCAL e roda seed, histórico, ingest e seed-demo. Nunca na VPS
	$(CLI) reset

jobs-docker: ## mesmo que `make reset` mas dentro do container api (após make up)
	$(COMPOSE_LOCAL) exec api python -m app.cli reset

# ---------------------------------------------------------------- deploy e backup (VPS_HOST e VPS_DIR no .env)

deploy: ## rsync de data/ + git pull + compose up --build na VPS
	@test -n "$(VPS_HOST)" || (echo "defina VPS_HOST e VPS_DIR no .env"; exit 1)
	rsync -az --delete --exclude 'derived/' data/ $(VPS_HOST):$(VPS_DIR)/data/
	ssh $(VPS_HOST) 'cd $(VPS_DIR) && git pull --ff-only && docker compose -f infra/compose.yml --project-directory . up -d --build'

backup: ## pg_dump da VPS para backups/enter-<data>.sql.gz
	@test -n "$(VPS_HOST)" || (echo "defina VPS_HOST e VPS_DIR no .env"; exit 1)
	@mkdir -p backups
	ssh $(VPS_HOST) 'cd $(VPS_DIR) && docker compose -f infra/compose.yml --project-directory . exec -T db pg_dump -U $${POSTGRES_USER:-enter} $${POSTGRES_DB:-enter}' | gzip > backups/enter-$$(date +%Y%m%d-%H%M).sql.gz
	@ls -la backups | tail -1

.PHONY: help hooks check check-commits check-memory-bank check-secrets lint test install up up-prod down logs psql dev-api dev-web seed historico ingest seed-demo reset-demo reset jobs-docker deploy backup
