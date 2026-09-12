# Features

Estado: ✅ pronta · 🔧 em andamento · ⬜ planejada. Edite a linha; não adicione histórico.

| Feature | Req | Dono | Estado | Onde |
|---|---|---|---|---|
| Regras de colaboração e memory-bank | — | Lucas | ✅ | `CLAUDE.md`, `memory-bank/` |
| CI de PR: commits, memory-bank, segredos, testes por componente | — | Lucas | ✅ | `.github/workflows/ci.yml` (core: pytest; api e engine: `uv sync --frozen` + ruff + pytest, api com Postgres de serviço; web: tsc + build; compose: config); testes da API criam `enter_test` se faltar |
| Parsing dos CSVs da Enter e UF por número CNJ | — | Lucas | ✅ | `src/core/core/colunas.py`, `src/core/core/cnj.py` |
| Contratos P1/P3 e stub do modelo | — | Lucas | ✅ | contratos em `src/core/core/{caso,modelo,docs}.py`; `StubModelo` (lookup no histórico) em `src/api/app/stubs.py`; seleção por env em `plugins.py`; sem P3 não há stub de extração: `carregar_extrator` devolve None e o portal mostra só flags, scores e recomendação (decisão 27) |
| Política de custo esperado e backtest | 1, 2, 5 | Lucas; P1 calibra | ✅ | núcleo em `src/core/core/politica.py` (11 testes); backtest com resultados reais em `src/api/app/services/backtest.py` (~15 ms nos 60k) |
| Auth por cookie, papéis advogado/gestor | 3 | Lucas | ✅ | `src/api/app/auth.py`, `routers/auth.py`; seed com 8 usuários (`senha123`) em `services/seed.py` |
| Jobs: seed, load-historico, ingest, seed-demo, reset-demo, reset | — | Lucas | ✅ | `python -m app.cli`; `seed-demo` lê `data/exemplos/sinteticos_processos.csv` (340 processos só com UF, sub-assunto, valor da causa, flags e escritório, todos pendentes; sem decisões simuladas, o painel do gestor só mostra decisões reais; decisão 28) |
| Lista e detalhe de processos, arquivos | 3 | Lucas | ✅ | `routers/processos.py`, `routers/files.py`; `pages/advogado/{Casos,Caso}.tsx` (lista com filtro todos/pendentes/decididos, busca por número, medidor de 6 subsídios e linha clicável; PDFs em nova aba, abertos ficam marcados) |
| Recomendação gravada sob a política ativa | 1, 2, 4 | Lucas | ✅ | `GET /processos/{id}/recomendacao` → `services/recomendacao.py` (get_or_create com ON CONFLICT) |
| Decisão com aderência, justificativa e aprovação | 4 | Lucas | ✅ | `POST /processos/{id}/decisoes`; regras em `services/recomendacao.avaliar_decisao`; minutas e contato adverso só com P3 plugado |
| Resultado da negociação | 5 | Lucas | ✅ | `POST /decisoes/{id}/resultado` (colunas em `decisoes`) |
| Eventos de auditoria | 4 | Lucas | ✅ | `POST /eventos` + eventos automáticos abriu_caso, viu_recomendacao, abriu_documento |
| Dashboard de aderência (números) | 4 | Lucas | ✅ | `GET /dashboard/aderencia` → `services/metricas.py` (por escritório, advogado, semana, justificativas, % sem ver recomendação) |
| Dashboard de efetividade (números) | 5 | Lucas | ✅ | `GET /dashboard/efetividade` (aceite real vs hipótese, desconto, economia realizada, backtest da política ativa, ModeloInfo) |
| Políticas: simular, publicar, versões | 1, 5 | Lucas | ✅ | `routers/politicas.py`, `services/backtest.py`; `ativar` grava `resumo_backtest`; `/api/internal/reload-historico` |
| Link mágico `/demo` para a banca | 3 | Lucas | ✅ | `GET /api/demo?t=` reserva caso livre da Banca Demo por 15 min, rate limit 20/min |
| Front básico: login, casos, caso, casca do painel, política, aprovações, tema visual da Enter | 3, 4, 5 | Lucas | ✅ | `pages/{Login,advogado/*,gestor/*}.tsx`; painel faz poll de 5 s; política simula com debounce de 300 ms e publica com diff; identidade visual em `theme.css` + `main.tsx` (decisão 29); P4/P5 polem a partir daqui |
| Compose, Caddy, deploy VPS, standby homelab, backup | — | Lucas | 🔧 | `make up` + `make jobs-docker` testados localmente via Caddy em :8080; `make deploy`/`make backup` escritos (VPS_HOST/VPS_DIR no .env) mas VPS e standby ainda não subiram |
| Clone limpo sobe sem dados da Enter: modelo exportado, resumo do backtest, processos sintéticos nossos | — | Lucas; P1 | ✅ | modelos em `models/*.json`, `docs/backtest/resumo.json`, `data/exemplos/sinteticos.csv` (engine) e `sinteticos_processos.csv` (portal) |
| Modelo de perda (logística calibrada + tabela de segmentos) e razão de condenação | 1, 2 | P1 | ✅ | `src/enteros/policy/{model,ratio}.py` → `models/*.json`; AUC 0,923 OOF. Scores para o portal via adapter (in-sample da logística); OOF opcional por `data/derived/historico_scored.csv` |
| Engine de valor esperado, faixas, escada de negociação e backtest do engine | 1, 2, 5 | P1 | ✅ | `src/enteros/policy/{engine,negotiation}.py`, `policy.yaml`, `src/enteros/backtest/`, `docs/backtest/`, `make backtest` |
| API própria do engine (`POST /recomendacao`) | 3 | P1 | ✅ | `src/enteros/api/main.py`, `make engine-api` (:8001) |
| Integração engine → portal (adapter `ModeloScores`) | 1, 2 | Lucas | ✅ | `src/api/app/modelo_enteros.py` (padrão de `MODEL_IMPL`); `load-historico` pontua os 60k com a logística do engine quando não há `historico_scored.csv`; 4 testes |
| Resumo dos principais pontos de um PDF (OCR + OpenAI) | 3 | P3 | ✅ | `src/extractor/extractor/{leitura,resumo,__main__}.py`; `make resumo PDF=caminho.pdf` (precisa de `OPENAI_API_KEY` no `.env`); texto nativo por página, OCR local só nas escaneadas; ainda não aparece no portal |
| Extração LLM dos PDFs + sinais de alerta | 1, 3 | P3 | ⬜ | `src/extractor` |
| Análise e minutas em linguagem jurídica | 3 | P3 | ⬜ | `src/extractor` |
| Portal do advogado polido + vídeo | 3 | P4 | ⬜ | `pages/advogado`, `docs/video.*` |
| Gráficos do painel e tela de política | 4, 5 | P5 | ⬜ | `pages/gestor` |
| Slides, README e SETUP finais | — | P5 | ⬜ | `docs/`, `SETUP.md`, `README.md` |
