.DEFAULT_GOAL := help
UV ?= uv
# Força o índice público mesmo em máquinas com espelho corporativo configurado no uv do usuário.
UVENV := UV_DEFAULT_INDEX=https://pypi.org/simple
PY := PYTHONPATH=src .venv/bin/python
RAW ?= data/raw/Hackaton_Enter_Base_Candidatos.xlsx

help: ## lista os alvos
	@grep -hE '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

setup: ## cria .venv com uv e instala dependências (inclui dev)
	$(UVENV) $(UV) sync --extra dev

data: ## carrega a base (xlsx em $(RAW) ou data/exemplos/sinteticos.csv) e salva cache parquet
	$(PY) -m enteros.data.load --raw $(RAW)

train: ## ajusta tabela de segmentos, logística calibrada e quantis de condenação; salva em models/
	$(PY) -m enteros.policy.model --raw $(RAW)

backtest: ## replay da política nos 60k com sensibilidade; gera docs/backtest/resumo.md e gráficos
	$(PY) -m enteros.backtest.report --raw $(RAW)

sinteticos: ## gera data/exemplos/sinteticos.csv (dados nossos, sem linhas da Enter) a partir dos modelos
	$(PY) -m enteros.sinteticos --raw $(RAW)

api: ## sobe a API em http://localhost:8000 (docs em /docs)
	PYTHONPATH=src .venv/bin/uvicorn enteros.api.main:app --reload --port 8000

test: ## roda os testes
	$(PY) -m pytest -q

demo: data train backtest test ## pipeline completo: dados → modelos → backtest → testes

.PHONY: help setup data train backtest sinteticos api test demo
