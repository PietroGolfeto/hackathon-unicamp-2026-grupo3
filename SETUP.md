# Setup e execução

Política de acordos do Banco UFMG: API (FastAPI + Postgres), portal do advogado e painel do gestor (React), com modelo (P1) e extração de documentos (P3) plugáveis. Detalhes de arquitetura em `memory-bank/arquitetura.md`.

## Pré-requisitos

- **Docker** com Compose v2 (caminho recomendado), **ou**
- Python 3.12 (com [`uv`](https://docs.astral.sh/uv/) de preferência), Node 20 e um Postgres 16.

## 1. Configurar

```bash
cp .env.example .env          # ajuste SECRET_KEY e DEMO_TOKEN se for expor
make hooks                    # verificações locais de commit (uma vez por clone)
```

Dados da organização (não versionados; a API sobe sem eles, só a simulação da política fica desabilitada):

```
data/
├── Hackaton_Enter_Base_Candidatos.xlsx - Resultados dos processos.csv
├── Hackaton_Enter_Base_Candidatos.xlsx - Subsídios disponibilizados.csv
└── exemplos/<numero-cnj>/{autos,subsidios}/*.pdf      # as 2 pastas de processos exemplo
```

## 2. Subir com Docker (tudo em `http://localhost:8080`)

```bash
make up            # db + api + caddy, sem TLS
make jobs-docker   # cria tabelas, seed, carrega os CSVs, ingere os exemplos, gera a demo
```

Abra `http://localhost:8080`. Usuários (senha `senha123`):

| E-mail | Papel |
|---|---|
| `adv1@escritorio-a` (também `adv2@…`, `adv1@escritorio-b`, …) | advogado |
| `gestor@banco-ufmg` | gestor |

Link mágico para a banca: `http://localhost:8080/api/demo?t=<DEMO_TOKEN>` loga um advogado da "Banca Demo" e abre um caso reservado só para aquele celular.

## 3. Desenvolvimento sem Docker na API/front

```bash
make install       # .venv com core+api e npm install do web
make up            # ou aponte DATABASE_URL do .env para um Postgres seu
make reset         # recria o banco LOCAL e roda todos os jobs
make dev-api       # http://localhost:8000/api/docs
make dev-web       # http://localhost:5173 (proxy de /api para :8000)
```

Jobs individuais: `make seed`, `make historico`, `make ingest`, `make seed-demo`, `make reset-demo` (apaga só decisões, eventos e recomendações; use antes de cada ensaio).

## 4. Testes e verificações

```bash
make check         # segredos, memory-bank, commits, ruff, pytest (core e api), tsc e build do web
```

Os testes da API usam um Postgres real em `DATABASE_URL` (padrão `…localhost:5432/enter_test`, crie o banco com `CREATE DATABASE enter_test`). Sem banco acessível eles são pulados com aviso.

## 5. Plugar modelo (P1) e extração (P3)

- `MODEL_IMPL=model.predict:Modelo` e `EXTRACTOR_IMPL=extractor.pipeline:Extrator` no `.env`; a classe precisa ser instanciável sem argumentos e seguir `memory-bank/contratos.md`.
- Alternativa por arquivo: `data/derived/historico_scored.csv` (scores OOF dos 60k), `data/derived/extraidos/<numero>.json` e `data/derived/scores/<numero>.json`. O `ingest` e o `load-historico` preferem o arquivo quando ele existe.
- Import quebrado não derruba nada: a API loga e usa o stub, e a UI mostra o badge "stub".

## 6. Deploy na VPS

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
| `SECRET_KEY` | assina o cookie de sessão (12 h) |
| `DEMO_TOKEN` | token do link `/api/demo?t=` |
| `DOMAIN` | `:8080` (sem TLS) ou o domínio real |
| `DATA_DIR` | onde estão os CSVs e `exemplos/` (`/data` dentro do compose) |
| `MODEL_IMPL`, `EXTRACTOR_IMPL` | implementações de P1 e P3 |
| `OPENAI_API_KEY` | só o extractor de P3 usa |
| `VPS_HOST`, `VPS_DIR` | `make deploy` e `make backup` |

## Estrutura

```
src/core        contratos, política em numpy, parsing (pacote `core`)
src/api         FastAPI + SQLAlchemy 2 + CLI de jobs (pacote `app`)
src/web         React 19 + Vite + Mantine (portal do advogado e painel do gestor)
src/model       P1 · src/extractor  P3
infra/          compose, Caddyfile, Dockerfiles
data/exemplos   processos sintéticos nossos (CSV) e pastas dos exemplos reais (ignoradas)
memory-bank/    estado vivo do projeto: leia antes de mexer
```
