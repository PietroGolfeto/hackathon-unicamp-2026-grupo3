# Arquitetura

Estado: ✅ existe · 🔧 em andamento · ⬜ planejado. Troque o marcador na própria linha quando o estado mudar.

## Estado atual
✅ Documentação e regras: `CLAUDE.md`, `memory-bank/`
✅ CI de PR e hooks locais: `.github/workflows/ci.yml`, `scripts/`, `Makefile` (`make hooks`, `make check`)
✅ `src/core`: pacote `core` com parsing dos CSVs, UF por CNJ, contratos P1/P3 e política em numpy, 32 testes
✅ `src/api`: FastAPI completa (auth, processos, recomendação, decisão, resultado, eventos, políticas, dashboards, aprovações, demo, arquivos) + CLI de jobs; 20 testes contra Postgres
✅ `src/web`: Vite + React 19 + Mantine 8 + TanStack Query + react-router 7; login, casos, caso, painel, política e aprovações com a identidade visual da Enter (Geist, Noto Serif, neutros e laranja; animações curtas); `npm run build` = tsc estrito + vite
🔧 `infra/` + `Makefile`: `make up` sobe db/api/caddy em :8080 (testado), `make jobs-docker` roda os jobs no container, `make deploy`/`make backup` para a VPS; VPS e standby ainda não subiram
✅ `src/enteros` (P1, fase 1): loader da planilha, tabela de segmentos + logística calibrada (AUC 0,923 OOF), razão de condenação por UF×sub-assunto, engine de valor esperado com escada de negociação, backtest com resultados reais (`docs/backtest/`), API própria (:8001) e 16 testes em `tests/`
✅ integração engine → portal: `src/api/app/modelo_enteros.py` (adapter `ModeloScores`, padrão de `MODEL_IMPL`); histórico dos 60k pontuado pela logística do engine
✅ `src/extractor`: pacote `extractor` (P3, base por Lucas): PDFs/TXT → validação de segurança → brief determinístico (≈1/3 do texto) → uma chamada OpenAI com saída estruturada → `DadosExtraidos` + `Analise`; cache em disco por conteúdo; minutas por template; CLI `make extrair`; benchmark `make bench-extractor`; 38 testes com dublê do LLM

## Visão geral
```
advogado (celular/desktop) ─┐
gestor do banco ────────────┤─ HTTPS ─ Caddy ─┬─ /api/*  ─ FastAPI ─ Postgres
                            │                  └─ /*      ─ SPA React (estático)
P1 engine (src/enteros) ─ modelos em models/*.json + policy.yaml ─▶ adapter app/modelo_enteros.py ─▶ scores por processo e dos 60k ─▶ API
                         └─ make backtest ─▶ docs/backtest/ (números do deck)
P3 extração (src/extractor) ─ PDFs → segurança → brief → OpenAI (cache em data/cache/extractor) ─▶ dados_extraidos + analise ─▶ job ingest ─▶ Postgres
                         · sem OPENAI_API_KEY responde só do cache; sem cache nada é inferido (decisão 27)
```

## Duas políticas na fase 1, uma base
**Engine (P1)** é a política de referência: `policy.yaml` + modelos em JSON → faixa, decisão, escada e o backtest que dá o número financeiro do deck (economia de 31% vs defender tudo, acordo em 36% dos casos). **API do portal** é a camada operacional: grava a recomendação que o advogado viu, mede aderência e efetividade e deixa o gestor simular parâmetros ao vivo sobre os 60k. A API já consome o modelo do engine via adapter (`app/modelo_enteros.py`): P(êxito), quantis de condenação e contribuições vêm de `models/*.json`. Falta P1 calibrar os `PoliticaParams` a partir do `policy.yaml` (mapa em `contratos.md`) para os dois backtests contarem a mesma história.

## Princípio central: scores ≠ política
Scores são a saída cara do modelo (P(êxito), condenação p20/p50/p80, contribuições), calculados uma vez por processo e gravados. Política é uma função pura barata em numpy sobre scores + parâmetros versionados. Isso permite: gestor simular parâmetros sobre 60 mil casos em < 100 ms, recomendação gravada no momento em que o advogado abre o caso, e P1 entregar só scores.

## Componentes
| Componente | Pasta | Estado | Responsabilidade |
|---|---|---|---|
| core | `src/core` | ✅ | parsing (`colunas.py`, `cnj.py`), contratos (`caso.py`, `modelo.py`, `docs.py`), política e backtest vetorizados (`politica.py`). Só pydantic e numpy |
| api | `src/api` | ✅ | FastAPI (`app/`): `main.py` com lifespan (create_all → seed → cache do histórico → plugins); `routers/{auth,processos,files,politicas,dashboard,aprovacoes,demo}.py`; `services/{seed,historico,backtest,recomendacao,metricas,ingest,seed_demo}.py`; `cli.py` |
| web | `src/web` | ✅ | SPA (`src/`): `api/client.ts` (tipos = schemas da API), `auth/useSession.ts`, `lib/format.ts` (BRL, %, datas), `lib/animacao.ts` (contagem animada), `theme.css` + tema Mantine em `main.tsx` (decisão 29: fontes, escalas `tinta`/`laranja`/`verde`/`vermelho`, keyframes `subir`/`escalonado`/`pulsar`/`crescer`), `components/{Layout,Marca,Icones,Badges,Stat}.tsx` (Layout com nav sublinhado em laranja e transição por rota; Stat conta até o valor), `pages/Login.tsx` (painel escuro + formulário, atalhos de demonstração), `pages/advogado/{Casos,Caso}.tsx` (cabeçalho → card da recomendação em duas colunas: decisão em serifa, banda da oferta sobre o valor da causa com marcador no sugerido, medidor de P(êxito), quantis de condenação e contribuições do modelo como barras a partir do centro, motivos e subsídios presentes/ausentes → documentos → decisão com seletor acordo/defesa, campos que se revelam e cronômetro → resultado; autor, sinais, análise, contato e minutas só aparecem quando P3 os entrega); `pages/gestor/{Painel,Politica,Aprovacoes}.tsx` (Painel: estatísticas com contagem animada e barras curtas de aderência, indicador ao vivo do poll; Política: simulação com totais política/defender/acordar em barras proporcionais e campo alterado destacado em laranja; gráficos completos são de P5). Dev: proxy `/api` → :8000 |
| enteros (P1) | `src/enteros`, `models/`, `tests/` | ✅ | pacote `enteros` do pyproject raiz: `data/load.py` (xlsx → base canônica, cache parquet), `policy/{model,ratio}.py` (logística + segmentos com shrinkage; quantis de condenação), `policy/{engine,negotiation,params}.py` + `policy.yaml` (valor esperado, faixas verde/amarela/vermelha, escada abertura/alvo/teto, VOI), `backtest/{replay,report}.py`, `api/main.py`. Substitui o `src/model` previsto |
| extractor | `src/extractor` | ✅ | P3 (base por Lucas). `texto.py` (lista autos/ e subsidios/ ou pasta plana; pdftotext do poppler, senão pypdf; TXT; limites de 20 MB e 200 páginas), `seguranca.py` (PDF: JavaScript, OpenAction/AA, Launch, anexos, XFA, cifra; texto: invisíveis e controle, blobs base64, instrução embutida PT/EN → linha removida + achado; decisão 31), `parsing.py` (tipo do documento por nome e conteúdo; fatos por regex; petição reduzida a cabeçalho, fatos, títulos do direito, pedidos, valor da causa, assinatura, procuração e nascimento do RG; subsídios a pares rótulo/valor + parágrafos com termos fortes; demonstrativo vira contagem de parcelas; brief ≤ 20k chars, petição com piso de 4,5k), `schema.py` (saída estrita do LLM: dados + análise + contradições + extras), `prompts.py` (`VERSAO_PROMPT` entra na chave do cache), `llm.py` (`responses.parse`, tokens; protocolo para dublês), `cache.py` (`sha256(arquivos + prompt + modelo + esquema)` → `data/cache/extractor/<chave>.json` + `por_numero/`), `pipeline.py` (`Extrator`: `preparar` → `processar` → `extrair`/`analisar` da mesma chamada; UF pelo CNJ e valor da causa da regex vencem o LLM; CPF sempre mascarado; DOCUMENTO_SUSPEITO por arquivo anômalo), `minutas.py` (template, decisão 32), `cli.py` (`python -m extractor <pasta> [--sem-llm --brief --forcar]`), `benchmark.py` (`python -m extractor.benchmark <pastas> [--stress --cache-dir]`, sem LLM: tokens e tempo por etapa, orçamento por tipo, baselines ingênuos, fatos-chave, leitores, calibração com o cache; `make bench-extractor` grava `docs/extractor/benchmark.md`) |
| ambiente | `pyproject.toml`, `uv.lock`, `Makefile` | ✅ | um `.venv` via uv workspace (raiz = enteros; membros `src/core`, `src/api`); `make install`; alvos do engine (`data`, `train`, `backtest`, `sinteticos`, `engine-api`, `demo`) e do portal no mesmo Makefile |
| infra | `infra/` | 🔧 | `compose.yml` (db, api, caddy; invocar com `--project-directory .`), `compose.local.yml` (porta 8080, sem TLS), `Caddyfile` (`{$DOMAIN}`), `api.Dockerfile` (uv `sync --frozen` do workspace + `models/`; `.dockerignore` deixa `data/`, `node_modules` e `.venv` fora do contexto), `web.Dockerfile` (node build → caddy) |
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
0. **Engine**: `make data` (xlsx em `data/raw/` ou `sinteticos.csv`) → `make train` grava `models/*.json` → `make backtest` grava `docs/backtest/resumo.{json,md}`, gráficos e o bloco marcado do README.
1. **Carga**: `load-historico` lê os 2 CSVs → merge → scores OOF de P1 (ou stub) → `historico_sentencas`. `ingest` lê `data/exemplos/<numero>/` → flags pelos nomes dos PDFs + UF pelo CNJ → `Extrator.extrair` (cache hit não chama a OpenAI; sem chave e sem cache o ingest para com `ErroConfiguracao`) → scores de P1 (ou stub) → `Extrator.analisar` (mesma chamada) → `processos`. Idempotente; nunca toca `decisoes`.
2. **Advogado abre caso**: `GET /processos/{id}/recomendacao` → get_or_create sob a política ativa → grava evento.
3. **Decisão**: `POST /processos/{id}/decisoes` → calcula `aderente`; divergência exige justificativa; valor fora da banda ou causa alta vira `pendente_aprovacao`; devolve minutas e contato adverso quando acordo e P3 está plugado (sem P3, nulos). Depois `POST /decisoes/{id}/resultado`.
4. **Gestor**: `POST /politicas/simular` roda a política sobre o histórico com resultados reais; `ativar` grava o resumo; painel lê agregados de `decisoes`/`eventos` e o resumo da política ativa.
5. **Banca**: `GET /api/demo?t=<token>` loga um advogado do escritório "Banca Demo", reserva um caso livre por 15 min (`FOR UPDATE SKIP LOCKED`) e redireciona para `/casos/{id}`; sem caso livre, vai para `/casos`.
6. **Aprovação**: `GET /aprovacoes` lista `pendente_aprovacao`; `POST /aprovacoes/{id}` aprova ou rejeita com comentário.

## Deploy
VPS com domínio: um Caddy com TLS automático servindo o `dist/` e fazendo proxy de `/api/*` para a API (mesma origem, sem CORS). Volume `caddy_data` persistido. Homelab roda o mesmo compose como standby permanente em `standby.<dominio>` via túnel; `pg_dump` da VPS para o homelab a cada 10 min. Dev e standby usam `infra/compose.local.yml` (porta 8080, sem TLS).
`data/` é montado só leitura no container; `data/cache/` é o único ponto gravável (cache do extractor), criado por `make up`. `make deploy` não sincroniza `cache/`, então a VPS extrai uma vez e cacheia lá. `data/` não é versionado: `make deploy` sincroniza por rsync para a VPS e faz `git pull` + `compose up --build`; `make backup` traz um `pg_dump`. Localmente: `make up` (compose com override sem TLS), `make dev-api`/`make dev-web` fora do Docker, jobs via `make seed|historico|ingest|seed-demo|reset-demo|reset` (rodam contra o `DATABASE_URL` do `.env`). Sem os CSVs da Enter a API sobe normalmente e a tela de simular avisa que o histórico não está carregado.

## Convenções de API
Prefixo `/api` (`/api/health`, `/api/docs`). Cookie HttpOnly assinado, 12 h. IDs inteiros nas URLs (número CNJ só em busca). Erros `{detail: "texto em português"}`. Datas ISO 8601. Dinheiro em número; formatação BRL só no front.
