# Arquitetura

Estado: ✅ existe · 🔧 em andamento · ⬜ planejado. Troque o marcador na própria linha quando o estado mudar.

## Estado atual
✅ Documentação e regras: `CLAUDE.md`, `memory-bank/`, `docs/plano-implementacao.md`
✅ CI de PR e hooks locais: `.github/workflows/ci.yml`, `scripts/`, `Makefile` (`make hooks`, `make check`)
🔧 `src/core`: pacote `core` com parsing dos CSVs e UF por CNJ, 17 testes; contratos e política ainda não
⬜ `src/api`, `src/web`, `src/model`, `src/extractor`, `infra/`: ainda não existem

## Visão geral
```
advogado (celular/desktop) ─┐
gestor do banco ────────────┤─ HTTPS ─ Caddy ─┬─ /api/*  ─ FastAPI ─ Postgres
                            │                  └─ /*      ─ SPA React (estático)
P1 modelo    ─ scores por processo + scores OOF dos 60k ─▶ jobs ingest / load-historico ─▶ Postgres
P3 extração  ─ dados dos PDFs, sinais, análise, minutas ─▶ job ingest ─────────────────▶ Postgres
```

## Princípio central: scores ≠ política
Scores são a saída cara do modelo (P(êxito), condenação p20/p50/p80, contribuições), calculados uma vez por processo e gravados. Política é uma função pura barata em numpy sobre scores + parâmetros versionados. Isso permite: gestor simular parâmetros sobre 60 mil casos em < 100 ms, recomendação gravada no momento em que o advogado abre o caso, e P1 entregar só scores.

## Componentes
| Componente | Pasta | Estado | Responsabilidade |
|---|---|---|---|
| core | `src/core` | 🔧 | parsing de CSV e número CNJ prontos (`colunas.py`, `cnj.py`); contratos pydantic e política em numpy ainda não. Só pydantic e numpy |
| api | `src/api` | ⬜ | FastAPI: auth por cookie, processos, recomendações, decisões, dashboards, políticas, arquivos, link de demo, CLI de jobs |
| web | `src/web` | ⬜ | SPA React + Vite + TS + Mantine: login, casos, caso, painel, política, aprovações |
| model | `src/model` | ⬜ | P1: treino XGBoost, `RealScorer`, export do histórico com scores OOF |
| extractor | `src/extractor` | ⬜ | P3: extração LLM dos PDFs, sinais de alerta, análise e minutas em linguagem jurídica |
| infra | `infra/` | ⬜ | compose (db, api, caddy), Caddyfile, Dockerfiles, compose local sem TLS |
| ci | `.github/`, `scripts/`, `Makefile` | ✅ | verificações de PR e testes por componente |

## Tabelas (8, Postgres, `create_all`, sem migrações)
| Tabela | Papel |
|---|---|
| `escritorios` | escritórios de advocacia + "Banca Demo" |
| `usuarios` | papel `advogado` (com escritório) ou `gestor` |
| `processos` | caso: numero CNJ, uf, sub_assunto, valor_causa, escritório, `subsidios`/`documentos`/`dados_extraidos`/`analise`/`scores` em jsonb, status, `reservado_ate` |
| `historico_sentencas` | 60k linhas + scores OOF; cacheado em DataFrame na API para o backtest |
| `politicas` | versão, `params` jsonb, ativa, `resumo_backtest` gravado ao ativar |
| `recomendacoes` | UNIQUE (processo, política): o que o advogado viu; snapshot dos scores e `motivos` |
| `decisoes` | append-only; aderente, tipo_desvio, status de aprovação, tempo de análise, docs abertos, e o resultado da negociação (`resultado`, `valor_final`, `resultado_em`) |
| `eventos` | abriu_caso, viu_recomendacao, abriu_documento |

## Fluxos
1. **Carga**: `load-historico` lê os 2 CSVs → merge → scores OOF de P1 (ou stub) → `historico_sentencas`. `ingest` lê `data/exemplos/<numero>/` → extração de P3 (ou stub) → scores de P1 (ou stub) → `processos`. Idempotente; nunca toca `decisoes`.
2. **Advogado abre caso**: `GET /processos/{id}/recomendacao` → get_or_create sob a política ativa → grava evento.
3. **Decisão**: `POST /processos/{id}/decisoes` → calcula `aderente`; divergência exige justificativa; valor fora da banda ou causa alta vira `pendente_aprovacao`; devolve minutas e contato adverso quando acordo. Depois `POST /decisoes/{id}/resultado`.
4. **Gestor**: `POST /politicas/simular` roda a política sobre o histórico com resultados reais; `ativar` grava o resumo; painel lê agregados de `decisoes`/`eventos` e o resumo da política ativa.
5. **Banca**: `GET /api/demo?t=<token>` loga um advogado do escritório "Banca Demo", reserva um caso livre por 15 min e redireciona para `/casos/{id}`.

## Deploy
VPS com domínio: um Caddy com TLS automático servindo o `dist/` e fazendo proxy de `/api/*` para a API (mesma origem, sem CORS). Volume `caddy_data` persistido. Homelab roda o mesmo compose como standby permanente em `standby.<dominio>` via túnel; `pg_dump` da VPS para o homelab a cada 10 min. Dev e standby usam `infra/compose.local.yml` (porta 8080, sem TLS).

## Convenções de API
Prefixo `/api`. Cookie HttpOnly assinado, 12 h. IDs inteiros nas URLs (número CNJ só em busca). Erros `{detail: "texto em português"}`. Datas ISO 8601. Dinheiro em número; formatação BRL só no front.
