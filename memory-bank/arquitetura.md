# Arquitetura

Estado: ✅ existe · 🔧 em andamento · ⬜ planejado. Troque o marcador na própria linha quando o estado mudar.

## Estado atual
✅ Documentação e regras: `CLAUDE.md`, `memory-bank/`
✅ CI de PR e hooks locais: `.github/workflows/ci.yml`, `scripts/`, `Makefile` (`make hooks`, `make check`)
✅ `src/core`: pacote `core` com parsing dos CSVs, UF por CNJ, contratos P1/P3 e política em numpy, 32 testes
✅ `src/api`: FastAPI completa (auth, processos, recomendação, decisão, resultado, eventos, políticas, dashboards, parecer IA sob demanda, aprovações, demo, arquivos) + CLI de jobs; 26 testes contra Postgres
✅ `src/web`: Vite + React 19 + Mantine 8 + Charts/Recharts + TanStack Query + react-router 7; casos, painel, política e aprovações com a identidade visual da Enter (Geist, Noto Serif, neutros e laranja; animações curtas); `npm run build` = tsc estrito + vite
🔧 `infra/` + `Makefile`: `make up` sobe db/api/caddy em :8080 (testado), `make jobs-docker` roda os jobs no container, `make deploy`/`make backup` para a VPS; VPS e standby ainda não subiram
✅ `src/enteros` (P1, fase 1): loader da planilha, tabela de segmentos + logística calibrada (AUC 0,923 OOF), razão de condenação por UF×sub-assunto, engine de valor esperado com escada de negociação, backtest com resultados reais (`docs/backtest/`), API própria (:8001) e 16 testes em `tests/`
✅ integração engine → portal: `src/api/app/modelo_enteros.py` (adapter `ModeloScores`, padrão de `MODEL_IMPL`); histórico dos 60k pontuado pela logística do engine
✅ `src/extractor`: pacote `extractor` (P3, base por Lucas): PDFs/TXT → validação de segurança → brief determinístico (≈1/3 do texto) → uma chamada OpenAI que devolve só `resumo` (≤ 5 bullets com fonte) e `contradicoes` → `DadosExtraidos` + `Analise` montados por regra em cima disso; cache em disco por conteúdo; minutas por template; CLI `make extrair`; benchmark `make bench-extractor`; gerador de PDF com prompt injection oculta `make exemplo-injecao`; 49 testes com dublê do LLM e 2 com a OpenAI real só sob `--llm` (`make test-llm`)

## Visão geral
```
advogado (celular/desktop) ─┐
gestor do banco ────────────┤─ HTTPS ─ Caddy ─┬─ /api/*  ─ FastAPI ─ Postgres
                            │                  └─ /*      ─ SPA React (estático)
P1 engine (src/enteros) ─ modelos em models/*.json + policy.yaml ─▶ adapter app/modelo_enteros.py ─▶ scores por processo e dos 60k ─▶ API
                         └─ make backtest ─▶ docs/backtest/ (números do deck)
P3 extração (src/extractor) ─ PDFs → segurança → brief → OpenAI devolve resumo em bullets + contradições (cache em data/cache/extractor) ─▶ regras montam dados_extraidos + analise ─▶ job ingest ─▶ Postgres
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
| api | `src/api` | ✅ | FastAPI (`app/`): `main.py` com lifespan (create_all → seed → cache do histórico → plugins); `routers/{auth,processos,preparacao,files,politicas,dashboard,aprovacoes,demo}.py`; `services/{seed,historico,backtest,recomendacao,metricas,parecer_ia,ingest,seed_demo,mock_painel,preparacao}.py`; `cli.py` |
| web | `src/web` | ✅ | SPA (`src/`): `api/client.ts` (tipos = schemas da API), `auth/useSession.ts`, `lib/format.ts` (BRL, %, datas), `lib/animacao.ts` (contagem animada), `theme.css` + tema Mantine em `main.tsx` (decisão 29), `components/{Layout,Marca,Icones,Badges,Stat}.tsx` (seletor Advogado/Gestor e navegação por papel); `RequireAuth` entra sozinho na conta de demonstração; `pages/advogado/{casos,caso}/` mostram recomendação, resumo em bullets + contradições (`CardAnalise`), documentos, decisão e resultado; uma pasta por tela, cada uma com `*.page.tsx` (só composição), `hooks/` (estado, queries e mutations), `components/`, `*.const.ts` e `*.types.ts`; `pages/gestor/{Painel,Politica,Aprovacoes}.tsx` (Painel é a entrada única: impacto financeiro e KPIs animados, pulso de aderência, custo/desfecho, fila com parecer IA e separação entre potencial histórico e operação real; Política e Aprovações são rotas contextuais). Dev: proxy `/api` → :8000 |
| enteros (P1) | `src/enteros`, `models/`, `tests/` | ✅ | pacote `enteros` do pyproject raiz: `data/load.py` (xlsx → base canônica, cache parquet), `policy/{model,ratio}.py` (logística + segmentos com shrinkage; quantis de condenação), `policy/{engine,negotiation,params}.py` + `policy.yaml` (valor esperado, faixas verde/amarela/vermelha, escada abertura/alvo/teto, VOI), `backtest/{replay,report}.py`, `api/main.py`. Substitui o `src/model` previsto |
| extractor | `src/extractor` | ✅ | P3 (base por Lucas). `texto.py` (lista autos/ e subsidios/ ou pasta plana; pdftotext do poppler, senão pypdf; TXT; limites de 20 MB e 200 páginas), `seguranca.py` (PDF: JavaScript, OpenAction/AA, Launch, anexos, XFA, cifra; texto: invisíveis e controle, blobs base64, instrução embutida PT/EN → linha removida + achado; decisão 39), `parsing.py` (tipo do documento por nome e conteúdo; fatos por regex; petição reduzida a cabeçalho, fatos, títulos do direito, pedidos, valor da causa, assinatura, procuração e nascimento do RG; subsídios a pares rótulo/valor + parágrafos com termos fortes; demonstrativo vira contagem de parcelas; brief ≤ 20k chars, petição com piso de 4,5k), `schema.py` (saída estrita do LLM: só `resumo`, até 5 bullets de uma linha com a fonte entre colchetes, e `contradicoes`; decisão 49), `prompts.py` (`VERSAO_PROMPT` entra na chave do cache), `llm.py` (`responses.parse`; tokens de entrada, saída, cache e raciocínio, latência; protocolo para dublês), `cache.py` (`sha256(arquivos + prompt + modelo + esquema)` → `data/cache/extractor/<chave>.json` + `por_numero/`), `pipeline.py` (`Extrator`: `preparar` → `processar` → `extrair`/`analisar` da mesma chamada; autor, advogado, comarca e valor da causa da petição por regex, contrato por rótulos e indícios dos subsídios, UF pelo CNJ, sinais só por regra (decisão 42), `confianca` = completude do material; bullets e contradições que citam subsídio ausente saem; comentário por documento = bullet que o cita; DOCUMENTO_SUSPEITO por arquivo anômalo; cache reaplica as regras atuais à saída gravada do LLM), `minutas.py` (template, decisão 40), `cli.py` (`python -m extractor <pasta> [--sem-llm --brief --forcar]`), `benchmark.py` (`python -m extractor.benchmark <pastas> [--stress --cache-dir]`, sem LLM: tokens e tempo por etapa, orçamento por tipo, baselines ingênuos, fatos-chave, leitores, calibração com o cache; `make bench-extractor` grava `docs/extractor/benchmark.md`), `injecao.py` (`python -m extractor.injecao`: recria um processo exemplo com texto oculto no PDF — render mode 3 e branco 1 pt, nas margens para o pdftotext -layout não fundir com o corpo — para exercitar a defesa de `seguranca.py`) |
| ambiente | `pyproject.toml`, `uv.lock`, `Makefile` | ✅ | um `.venv` via uv workspace (raiz = enteros; membros `src/core`, `src/api`); `make install`; alvos do engine (`data`, `train`, `backtest`, `sinteticos`, `engine-api`, `demo`) e do portal no mesmo Makefile |
| infra | `infra/` | 🔧 | `compose.yml` (db, api, caddy; invocar com `--project-directory .`), `compose.local.yml` (porta 8080, sem TLS), `Caddyfile` (`{$DOMAIN}`), `api.Dockerfile` (uv `sync --frozen` do workspace + `models/` + `docs/backtest/resumo.json`; `.dockerignore` deixa `data/`, `docs/` (exceto o resumo), `node_modules` e `.venv` fora do contexto), `web.Dockerfile` (node build → caddy) |
| ci | `.github/`, `scripts/`, `Makefile` | ✅ | verificações de PR e testes por componente |

## Tabelas (9, Postgres, `create_all`, sem migrações)
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
| `pareceres_justificativa` | um parecer consultivo da IA por decisão divergente; conteúdo estruturado e persistido |

## Fluxos
0. **Engine**: `make data` (xlsx em `data/raw/` ou `sinteticos.csv`) → `make train` grava `models/*.json` → `make backtest` grava `docs/backtest/resumo.{json,md}`, gráficos e o bloco marcado do README.
1. **Carga**: `make mocks-advogado` (`scripts/mocks_advogado.sh`) monta `data/exemplos/<numero>/{autos,subsidios}` a partir de `data/mock-para-tela-advogado/Caso_NN/` (PDFs da Enter, não versionados) e deriva um terceiro caso sem o extrato, para cobrir as três saídas do engine. `load-historico` lê os 2 CSVs → merge → scores OOF de P1 (ou stub) → `historico_sentencas`. `ingest` lê `data/exemplos/<numero>/` → flags pelos nomes dos PDFs + UF pelo CNJ → `Extrator.extrair` (cache hit não chama a OpenAI; sem chave e sem cache o ingest para com `ErroConfiguracao`) → scores de P1 (ou stub) → `Extrator.analisar` (mesma chamada) → `processos`. Idempotente; nunca toca `decisoes`.
1b. **Advogado abre a lista**: `POST /api/preparacao` (202) dispara em thread o ingest das pastas de `data/exemplos/` — extração LLM, scores e recomendação sob a política ativa — e o front faz poll de 1,5 s em `GET /api/preparacao` até `pronto`, mostrando o progresso (decisão 14: poll, nunca websocket). Uma execução por vez (lock de módulo; a API roda com 1 worker) e idempotente: o que já está no banco não roda de novo e o cache do extractor cobre o resto, então da segunda vez em diante nada chama a OpenAI. Um caso que falha não impede os outros: vai em `erro` e a tela mostra o que deu certo.
2. **Advogado abre caso**: `GET /processos/{id}/recomendacao` → get_or_create sob a política ativa → grava evento.
3. **Decisão**: `POST /processos/{id}/decisoes` → calcula `aderente`; divergência exige justificativa; valor fora da banda ou causa alta vira `pendente_aprovacao`; devolve minutas e contato adverso quando acordo e P3 está plugado (sem P3, nulos). Depois `POST /decisoes/{id}/resultado`.
4. **Gestor**: painel lê aderência de `decisoes`/`eventos`, efetividade operacional e o potencial versionado do engine; `POST /dashboard/desvios/{id}/parecer` chama a OpenAI sob demanda e persiste uma análise consultiva; Política e Aprovações são rotas contextuais.
5. **Banca**: `GET /api/demo?t=<token>` loga um advogado do escritório "Banca Demo", reserva um caso livre por 15 min (`FOR UPDATE SKIP LOCKED`) e redireciona para `/casos/{id}`; sem caso livre, vai para `/casos`.
6. **Aprovação**: `GET /aprovacoes` lista `pendente_aprovacao`; `POST /aprovacoes/{id}` aprova ou rejeita com comentário.

## Deploy
VPS com domínio: um Caddy com TLS automático servindo o `dist/` e fazendo proxy de `/api/*` para a API (mesma origem, sem CORS). Volume `caddy_data` persistido. Homelab roda o mesmo compose como standby permanente em `standby.<dominio>` via túnel; `pg_dump` da VPS para o homelab a cada 10 min. Dev e standby usam `infra/compose.local.yml` (porta 8080, sem TLS).
`data/` é montado só leitura no container; `data/cache/` é o único ponto gravável (cache do extractor e PDF de exemplo dos processos sintéticos), criado por `make up`. `make deploy` não sincroniza `cache/`, então a VPS extrai uma vez e cacheia lá. `data/` não é versionado: `make deploy` sincroniza por rsync para a VPS e faz `git pull` + `compose up --build`; `make backup` traz um `pg_dump`. Localmente: `make up` (compose com override sem TLS), `make dev-api`/`make dev-web` fora do Docker, jobs via `make seed|historico|ingest|seed-demo|reset-demo|reset` (rodam contra o `DATABASE_URL` do `.env`) e `make mock-painel` só em desenvolvimento (decisão 44; trava fora de banco local). Sem os CSVs da Enter a API sobe normalmente e a tela de simular avisa que o histórico não está carregado.

## Convenções de API
Prefixo `/api` (`/api/health`, `/api/docs`). Cookie HttpOnly assinado, 12 h. IDs inteiros nas URLs (número CNJ só em busca). Erros `{detail: "texto em português"}`. Datas ISO 8601. Dinheiro em número; formatação BRL só no front.
