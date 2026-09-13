.DEFAULT_GOAL := help
BASE ?= origin/main
HEAD ?= HEAD
VENV := .venv
PY := $(if $(wildcard $(VENV)/bin/python),$(VENV)/bin/python,python3)
UV := $(shell command -v uv 2>/dev/null)
# Força o índice público mesmo em máquinas com espelho corporativo configurado no uv do usuário.
UVENV := UV_DEFAULT_INDEX=https://pypi.org/simple
COMPOSE := docker compose -f infra/compose.yml --project-directory .
COMPOSE_LOCAL := $(COMPOSE) -f infra/compose.local.yml
CLI := PYTHONPATH=src/api $(PY) -m app.cli
# testes da API sempre num banco próprio: nunca o DATABASE_URL do .env (drop_all!)
TEST_DATABASE_URL ?= postgresql+psycopg://enter:enter@localhost:5432/enter_test
# planilha bruta da Enter para o engine (não versionada); sem ela roda sobre data/exemplos/sinteticos.csv
RAW ?= data/raw/Hackaton_Enter_Base_Candidatos.xlsx
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

lint: ## ruff em core, api e extractor; tsc no web
	$(PY) -m ruff check src/core src/api src/extractor
	@if [ -f src/web/package.json ]; then echo "→ web (tsc)"; cd src/web && npm run lint --if-present; fi

test: ## testes de todos os componentes (core, api com Postgres, engine, web build)
	@if [ -f src/core/pyproject.toml ]; then echo "→ core"; $(PY) -m pytest -q src/core; fi
	@if [ -f src/api/pyproject.toml ]; then echo "→ api"; DATABASE_URL=$(TEST_DATABASE_URL) $(PY) -m pytest -q src/api; fi
	@if [ -d tests ]; then echo "→ engine"; $(PY) -m pytest -q tests; fi
	@if [ -f src/extractor/pyproject.toml ]; then echo "→ extractor"; $(PY) -m pytest -q src/extractor; fi
	@if [ -f src/web/package.json ]; then echo "→ web"; cd src/web && npm run build; fi
	@echo "✓ testes ok"

# ---------------------------------------------------------------- ambiente local

install: ## .venv com uv (core, api e engine no mesmo workspace) e npm install do web
	@if [ -n "$(UV)" ]; then $(UVENV) uv sync --extra dev; \
	else python3 -m venv $(VENV) && $(VENV)/bin/pip install -q -e ".[dev]" -e src/core -e "src/api[test]"; fi
	@for p in model extractor; do if [ -f src/$$p/pyproject.toml ]; then $(VENV)/bin/pip install -q -e src/$$p; fi; done
	cd src/web && npm install --no-audit --no-fund
	@echo "✓ pronto: make up (docker) ou make dev-api + make dev-web; engine: make demo"

setup: install ## alias de install

up: ## sobe db, api e caddy em http://localhost:8080 (sem TLS)
	@mkdir -p data/cache
	$(COMPOSE_LOCAL) up -d --build

up-prod: ## sobe com TLS automático no DOMAIN do .env (VPS)
	$(COMPOSE) up -d --build

down: ## derruba os containers (mantém volumes)
	$(COMPOSE_LOCAL) down

logs: ## acompanha logs da api e do caddy
	$(COMPOSE_LOCAL) logs -f --tail=100 api caddy

psql: ## abre psql no Postgres do compose
	$(COMPOSE_LOCAL) exec db psql -U $${POSTGRES_USER:-enter} $${POSTGRES_DB:-enter}

dev-api: ## API do portal com reload em :8000 (usa .env e o Postgres de `make up` ou local)
	$(PY) -m uvicorn --app-dir src/api app.main:app --reload --port 8000

dev-web: ## Vite em :5173 com proxy de /api para :8000
	cd src/web && npm run dev

# ---------------------------------------------------------------- jobs de carga do portal (rodam onde estiver o DATABASE_URL)

seed: ## escritórios, usuários e política v1 (idempotente)
	$(CLI) seed

historico: ## carrega os 2 CSVs da Enter de data/ e avisa a API
	$(CLI) load-historico

ingest: ## lê data/exemplos/<numero>/ (autos e subsídios) para processos
	$(CLI) ingest

seed-demo: ## processos sintéticos avulsos, para dar volume ao painel do gestor; fora do reset
	$(CLI) seed-demo

mock-painel: ## SÓ DESENVOLVIMENTO: decisões sorteadas para ver o painel do gestor cheio
	$(CLI) mock-painel

reset-demo: ## apaga decisões, eventos e recomendações; mantém processos e políticas
	$(CLI) reset-demo

reset: ## recria o banco LOCAL e roda seed, histórico e ingest. Nunca na VPS
	$(CLI) reset

jobs-docker: ## mesmo que `make reset` mas dentro do container api (após make up)
	$(COMPOSE_LOCAL) exec api python -m app.cli reset

# ---------------------------------------------------------------- extração dos PDFs (src/extractor, P3)

extrair: ## roda o extractor numa pasta de processo: make extrair PASTA=data/exemplos/<numero> [ARGS="--sem-llm --brief"]
	@test -n "$(PASTA)" || (echo "uso: make extrair PASTA=<pasta do processo> [ARGS=...]"; exit 1)
	$(PY) -m extractor $(PASTA) $(ARGS)

exemplo-injecao: ## recria data/processos_exemplo/processo_prompt-injection: petição do processo_01 com injeções ocultas [ARGS=--forcar]
	$(PY) -m extractor.injecao $(ARGS)

bench-extractor: ## benchmark da compressão de tokens (sem LLM) → docs/extractor/benchmark.md; tiktoken via uv quando houver
	@mkdir -p docs/extractor
	$(if $(UV),$(UVENV) uv run --no-sync --with tiktoken python,$(PY)) -m extractor.benchmark docs/Caso_*/ \
	  src/extractor/tests/dados/*/ --stress --cache-dir data/cache/extractor --md docs/extractor/benchmark.md

mocks-advogado: ## data/mock-para-tela-advogado/Caso_NN/ -> data/exemplos/<numero>/{autos,subsidios} (+ caso derivado)
	./scripts/mocks_advogado.sh

exemplos-docs: ## copia docs/Caso_*/ (PDFs da Enter, não versionados) para data/exemplos/<numero>/{autos,subsidios}
	@for d in docs/Caso_*/; do \
	  n=$$(basename "$$d" | sed -E 's/^Caso_[0-9]+_//; s/([0-9]{7})-([0-9]{2})-([0-9]{4})-([0-9])-([0-9]{2})-([0-9]{4})/\1-\2.\3.\4.\5.\6/'); \
	  mkdir -p "data/exemplos/$$n/autos" "data/exemplos/$$n/subsidios"; \
	  for f in "$$d"*.pdf; do case "$$(basename "$$f")" in *Autos*|*autos*|*Peticao*|*peticao*) cp "$$f" "data/exemplos/$$n/autos/";; *) cp "$$f" "data/exemplos/$$n/subsidios/";; esac; done; \
	  echo "→ data/exemplos/$$n"; ls "data/exemplos/$$n"/*; \
	done

# ---------------------------------------------------------------- engine de política e backtest (src/enteros, P1)

data: ## carrega a base (xlsx em $(RAW) ou data/exemplos/sinteticos.csv) e salva cache parquet
	$(PY) -m enteros.data.load --raw $(RAW)

train: ## ajusta tabela de segmentos, logística calibrada e quantis de condenação; salva em models/
	$(PY) -m enteros.policy.model --raw $(RAW)

backtest: ## replay da política nos 60k com sensibilidade; gera docs/backtest/resumo.md e gráficos
	$(PY) -m enteros.backtest.report --raw $(RAW)

compare-models: ## compara variantes de modelo de P(perda) pelo custo de decisão OOF; gera docs/modelo/comparacao.{md,json}
	$(PY) -m enteros.policy.comparar --raw $(RAW)

scored: ## scores OOF dos 60k para o portal em data/derived/historico_scored.csv (não versionado)
	$(PY) -m enteros.backtest.scored --raw $(RAW)

analises: ## análises agregadas e figuras para a demo (severidade por UF, fronteira de política, aprendizado do aceite)
	$(PY) -m enteros.analise.relatorio --raw $(RAW)

sinteticos: ## gera data/exemplos/sinteticos.csv (dados nossos, sem linhas da Enter) a partir dos modelos
	$(PY) -m enteros.sinteticos --raw $(RAW)

engine-api: ## API do engine em http://localhost:8001/docs (o portal roda em :8000)
	$(PY) -m uvicorn enteros.api.main:app --reload --port 8001

demo: data train backtest test ## pipeline do engine: dados → modelos → backtest → testes

# ---------------------------------------------------------------- deploy e backup (VPS_HOST e VPS_DIR no .env)

deploy: ## rsync de data/ + git pull + compose up --build na VPS
	@test -n "$(VPS_HOST)" || (echo "defina VPS_HOST e VPS_DIR no .env"; exit 1)
	rsync -az --delete --exclude 'derived/' --exclude 'cache/' data/ $(VPS_HOST):$(VPS_DIR)/data/
	ssh $(VPS_HOST) 'cd $(VPS_DIR) && git pull --ff-only && docker compose -f infra/compose.yml --project-directory . up -d --build'

backup: ## pg_dump da VPS para backups/enter-<data>.sql.gz
	@test -n "$(VPS_HOST)" || (echo "defina VPS_HOST e VPS_DIR no .env"; exit 1)
	@mkdir -p backups
	ssh $(VPS_HOST) 'cd $(VPS_DIR) && docker compose -f infra/compose.yml --project-directory . exec -T db pg_dump -U $${POSTGRES_USER:-enter} $${POSTGRES_DB:-enter}' | gzip > backups/enter-$$(date +%Y%m%d-%H%M).sql.gz
	@ls -la backups | tail -1

.PHONY: help hooks check check-commits check-memory-bank check-secrets lint test install setup up up-prod down logs psql dev-api dev-web seed historico ingest seed-demo mock-painel reset-demo reset jobs-docker extrair exemplo-injecao bench-extractor exemplos-docs mocks-advogado data train backtest compare-models scored analises sinteticos engine-api demo deploy backup
