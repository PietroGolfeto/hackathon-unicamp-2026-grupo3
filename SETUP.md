# Setup e Execução

## Pré-requisitos
- [uv](https://docs.astral.sh/uv/) (instala o Python 3.12 sozinho) — ou Python ≥ 3.11 com `pip`
- `make`
- Opcional: a planilha `Hackaton_Enter_Base_Candidatos.xlsx` fornecida pela organização (não versionada)

## Instalação
```bash
make setup            # cria .venv e instala dependências (uv sync --extra dev)
cp .env.example .env  # opcional; nada é obrigatório para engine, backtest e API
```
Sem `uv`: `python -m venv .venv && .venv/bin/pip install -e ".[dev]"`.

## Dados
Coloque a planilha em `data/raw/Hackaton_Enter_Base_Candidatos.xlsx` (pasta ignorada pelo git).
Sem ela, tudo roda sobre `data/exemplos/sinteticos.csv` — 3 mil processos **fictícios gerados por nós** a partir
dos modelos (nenhuma linha da Enter é versionada). Com a planilha, os números do backtest são os da base real.

## Execução
```bash
make data       # valida e cacheia a base (parquet em data/cache/)
make train      # ajusta tabela de segmentos, logística calibrada e quantis de condenação → models/*.json
make backtest   # replay da política com resultados reais → docs/backtest/resumo.md + gráficos
make test       # 16 testes: casos 01/02, monotonicidade, escada, API, backtest
make api        # http://localhost:8000/docs
make demo       # data → train → backtest → test
```

Exemplo de chamada da API (Caso 02):
```bash
curl -s localhost:8000/recomendacao -H 'content-type: application/json' -d '{
  "uf": "AM", "sub_assunto": "Golpe", "valor_causa": 25000,
  "docs": {"comprovante": "presente", "demonstrativo": "presente", "laudo": "presente"},
  "conta_deposito_titular_autor": false, "liveness_presente": false,
  "parcelas_pagas": 8, "valor_parcela": 180, "saldo_devedor": 2748.38
}' | python -m json.tool
```

## Estrutura
```
src/enteros/
  config.py            constantes (colunas, docs, rótulos, caminhos)
  schemas.py           CaseFeatures / Recomendacao (pydantic)
  data/load.py         xlsx ou CSV sintético → base canônica
  policy/policy.yaml   parâmetros versionados da política
  policy/model.py      tabela de segmentos + logística calibrada (JSON em models/)
  policy/ratio.py      condenação/valor da causa dado perda, por UF × sub-assunto
  policy/negotiation.py curva de aceite, escada abertura/alvo/teto, decomposição
  policy/engine.py     decisão por valor esperado, faixas, VOI, regras duras
  backtest/            replay com resultados reais, sensibilidade, gráficos
  api/main.py          FastAPI
  sinteticos.py        gerador do CSV sintético
tests/                 pytest
docs/                  politica.md, premissas.md, backtest/
```
