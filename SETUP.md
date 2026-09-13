# Setup e execução

Política de acordos do Banco UFMG em duas camadas que compartilham a mesma base de 60 mil sentenças:

- **Engine de política e backtest** (`src/enteros`, P1): modelo de perda calibrado, valor esperado, escada de negociação e o backtest que gera os números do deck. Roda sem banco.
- **Portal e API** (`src/api`, `src/web`, `infra/`): FastAPI + Postgres + React. É onde o advogado vê a recomendação, decide e registra o resultado; onde o gestor mede aderência e efetividade e simula parâmetros.

Arquitetura e estado atual em `memory-bank/arquitetura.md`; contratos entre as partes em `memory-bank/contratos.md`.

## Pré-requisitos

- [`uv`](https://docs.astral.sh/uv/) (instala o Python 3.12 sozinho) e `make`
- Node 20 (portal) e **Docker** com Compose v2 (portal com Postgres; opcional se você tiver um Postgres 16 próprio)

## 1. Configurar

```bash
cp .env.example .env          # ponha a OPENAI_API_KEY; ajuste DOMAIN se for expor
make hooks                    # verificações locais de commit (uma vez por clone)
make install                  # .venv único (engine, core e api) + npm install do web
```

Dados tabulares da organização (não versionados; tudo sobe sem eles, com dados sintéticos nossos):

```
data/
├── Hackaton_Enter_Base_Candidatos.xlsx - Resultados dos processos.csv      # portal
├── Hackaton_Enter_Base_Candidatos.xlsx - Subsídios disponibilizados.csv    # portal
└── raw/Hackaton_Enter_Base_Candidatos.xlsx                                 # engine
```

Os PDFs dos três processos exemplo já estão versionados em `data/exemplos/<numero-cnj>/{autos,subsidios}/`
(decisão 19/45). Quem tiver as pastas originais da organização em `docs/Caso_*/` regenera os três com
`make exemplos-docs`.

## 2. Engine e backtest (sem banco)

```bash
make demo          # data → train → backtest → test
make backtest      # só o replay nos 60k: docs/backtest/resumo.md, gráficos e tabelas do README
make engine-api    # http://localhost:8001/docs  (POST /recomendacao)
```

Sem a planilha em `data/raw/`, tudo roda sobre `data/exemplos/sinteticos.csv` (3 mil processos fictícios; números ilustrativos). Parâmetros da política em `src/enteros/policy/policy.yaml`; premissas em `docs/premissas.md`.

Exemplo (Caso 02):
```bash
curl -s localhost:8001/recomendacao -H 'content-type: application/json' -d '{
  "uf": "AM", "sub_assunto": "Golpe", "valor_causa": 25000,
  "docs": {"comprovante": "presente", "demonstrativo": "presente", "laudo": "presente"},
  "conta_deposito_titular_autor": false, "liveness_presente": false,
  "parcelas_pagas": 8, "valor_parcela": 180, "saldo_devedor": 2748.38
}' | python -m json.tool
```

## 3. Portal com Docker (tudo em `http://localhost:8080`)

```bash
make up            # db + api + caddy, sem TLS
make jobs-docker   # cria tabelas, seed, carrega os CSVs e ingere os 3 processos exemplo
```

O portal abre no lado do advogado; o seletor no canto superior direito troca para o gestor a qualquer momento.

## 4. Portal sem Docker na API/front

```bash
make up            # ou aponte DATABASE_URL do .env para um Postgres seu
make reset         # recria o banco LOCAL e roda todos os jobs
make dev-api       # http://localhost:8000/api/docs
make dev-web       # http://localhost:5173 (proxy de /api para :8000)
```

Jobs individuais: `make seed`, `make historico`, `make ingest`, `make seed-demo`, `make reset-demo` (apaga só decisões, eventos e recomendações; use antes de cada ensaio).

Para ver o painel do gestor cheio durante o desenvolvimento: `make mock-painel` cria decisões, justificativas e resultados **sorteados** (decisão 44). Só roda contra banco local. **Rode `make reset-demo` antes de qualquer ensaio ou demonstração**, senão a banca vê número inventado como se fosse medido.

## 5. Testes e verificações

```bash
make check         # segredos, memory-bank, commits, ruff, pytest (core, api, engine), tsc e build do web
make test          # só os testes
```

Os testes da API usam um Postgres real em `TEST_DATABASE_URL` (padrão `…localhost:5432/enter_test`; o banco é criado se não existir). Sem Postgres acessível eles são pulados com aviso. Os do engine (`tests/`) rodam sobre `models/*.json` e o CSV sintético.

## 6. Plugar modelo (P1) e extração (P3) no portal

- `MODEL_IMPL=pacote.modulo:Classe` e `EXTRACTOR_IMPL=…` no `.env`; a classe precisa ser instanciável sem argumentos e seguir `memory-bank/contratos.md`.
- Alternativa por arquivo: `data/derived/historico_scored.csv` (scores OOF dos 60k), `data/derived/extraidos/<numero>.json` e `data/derived/scores/<numero>.json`. O `ingest` e o `load-historico` preferem o arquivo quando ele existe.
- Import quebrado não derruba nada: o modelo cai no stub (a UI mostra o badge "stub"); a extração fica desligada e o portal não mostra nada inferido dos documentos (autor, sinais, análise, minutas), só presença de subsídio, scores e recomendação.

## 7. Deploy na VPS

```bash
# no .env: DOMAIN=acordos.seudominio.com.br  VPS_HOST=usuario@ip  VPS_DIR=/srv/enter
make deploy        # rsync de data/ + git pull + compose up --build (TLS automático pelo Caddy)
make backup        # pg_dump para backups/
```

Na VPS, o primeiro start precisa de `docker compose -f infra/compose.yml --project-directory . exec api python -m app.cli reset` (ou os jobs individuais). Não recrie o volume `caddy_data`: ele guarda os certificados.

## Variáveis de ambiente

| Variável | Uso |
|---|---|
| `DATABASE_URL` | Postgres da API (fora do compose) |
| `POSTGRES_USER/PASSWORD/DB` | banco criado pelo compose |
| `DOMAIN` | `:8080` (sem TLS) ou o domínio real |
| `DATA_DIR` | onde estão os CSVs e `exemplos/` (`/data` dentro do compose) |
| `ENTEROS_RAW_XLSX` | planilha bruta para o engine (`make data/train/backtest`) |
| `MODEL_IMPL`, `EXTRACTOR_IMPL` | implementações de P1 e P3 no portal |
| `OPENAI_API_KEY`, `OPENAI_MODEL` | extração documental e parecer consultivo das divergências |
| `VPS_HOST`, `VPS_DIR` | `make deploy` e `make backup` |

## Estrutura

```
pyproject.toml   projeto raiz (pacote `enteros`) e workspace uv com src/core e src/api
src/enteros      engine: data/load, policy/{model,ratio,negotiation,engine,params,policy.yaml}, backtest/, api/, sinteticos
models/          modelos exportados em JSON (segmentos, logística, razão de condenação)
tests/           testes do engine
src/core         contratos, política operacional em numpy, parsing (pacote `core`)
src/api          FastAPI + SQLAlchemy 2 + CLI de jobs (pacote `app`)
src/web          React 19 + Vite + Mantine (portal do advogado e painel do gestor)
infra/           compose, Caddyfile, Dockerfiles
docs/            relatorio.md (relatório técnico do grupo), politica.md, premissas.md, backtest/ e analises/ (gerados)
data/exemplos    CSVs sintéticos nossos e os PDFs dos 3 processos exemplo
memory-bank/     estado vivo do projeto: leia antes de mexer
```
