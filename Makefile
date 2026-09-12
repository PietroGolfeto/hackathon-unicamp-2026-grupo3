.DEFAULT_GOAL := help
BASE ?= origin/main
HEAD ?= HEAD
PY ?= python3
UV := $(shell command -v uv 2>/dev/null)

help: ## lista os alvos disponíveis
	@grep -hE '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

hooks: ## instala os hooks de git deste clone (pre-commit e commit-msg)
	git config core.hooksPath scripts/hooks
	@echo "hooks instalados em scripts/hooks (desfazer: git config --unset core.hooksPath)"

check: check-secrets check-memory-bank check-commits test ## roda tudo que a CI roda

check-commits: ## valida mensagem e tamanho dos commits em BASE..HEAD
	scripts/check_commits.sh $(BASE) $(HEAD)

check-memory-bank: ## exige memory-bank atualizado nos commits de código em BASE..HEAD
	scripts/check_memory_bank.sh $(BASE) $(HEAD)

check-secrets: ## bloqueia segredos e dados versionados
	scripts/check_secrets.sh

test: ## roda os testes dos componentes que existirem (core, api, web)
	@if [ -f src/core/pyproject.toml ]; then echo "→ core"; \
	  if [ -n "$(UV)" ]; then uv run -q -p 3.12 --with pytest --with-editable src/core pytest -q src/core; \
	  else $(PY) -m pytest -q src/core; fi; fi
	@if [ -f src/api/pyproject.toml ] || [ -f src/api/requirements.txt ]; then echo "→ api"; $(PY) -m pytest -q src/api; fi
	@if [ -f src/web/package.json ]; then echo "→ web"; cd src/web && npm test --if-present; fi
	@echo "✓ testes ok"

.PHONY: help hooks check check-commits check-memory-bank check-secrets test
