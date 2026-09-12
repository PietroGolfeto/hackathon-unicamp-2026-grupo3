# Features

Estado: ✅ pronta · 🔧 em andamento · ⬜ planejada. Edite a linha; não adicione histórico.

| Feature | Req | Dono | Estado | Onde |
|---|---|---|---|---|
| Regras de colaboração e memory-bank | — | Lucas | ✅ | `CLAUDE.md`, `memory-bank/` |
| CI de PR: commits, memory-bank, segredos, testes por componente | — | Lucas | ✅ | `.github/workflows/ci.yml`, `scripts/`, `Makefile` |
| Parsing dos CSVs da Enter e UF por número CNJ | — | Lucas | ✅ | `src/core/core/colunas.py`, `src/core/core/cnj.py` |
| Contratos P1/P3 e stubs | — | Lucas | ✅ | contratos em `src/core/core/{caso,modelo,docs}.py`; `StubModelo` (lookup no histórico) e `StubExtrator` (regex nos autos) em `src/api/app/stubs.py`; seleção por env em `plugins.py` |
| Política de custo esperado e backtest | 1, 2, 5 | Lucas; P1 calibra | ✅ | núcleo em `src/core/core/politica.py` (11 testes); backtest com resultados reais em `src/api/app/services/backtest.py` (~15 ms nos 60k) |
| Auth por cookie, papéis advogado/gestor | 3 | Lucas | ✅ | `src/api/app/auth.py`, `routers/auth.py`; seed com 8 usuários (`senha123`) em `services/seed.py` |
| Jobs: seed, load-historico, ingest, seed-demo, reset-demo, reset | — | Lucas | ✅ | `python -m app.cli`; `seed-demo` lê `data/exemplos/sinteticos.csv` (340 processos; ~255 decisões simuladas em 8 semanas; 15% ficam pendentes como fila do advogado) |
| Lista e detalhe de processos, arquivos | 3 | Lucas | ✅ | `routers/processos.py`, `routers/files.py`; `pages/advogado/{Casos,Caso}.tsx` (PDFs em nova aba, abertos ficam marcados) |
| Recomendação gravada sob a política ativa | 1, 2, 4 | Lucas | ✅ | `GET /processos/{id}/recomendacao` → `services/recomendacao.py` (get_or_create com ON CONFLICT) |
| Decisão com aderência, justificativa e aprovação | 4 | Lucas | ✅ | `POST /processos/{id}/decisoes`; regras em `services/recomendacao.avaliar_decisao`; devolve minutas e contato adverso |
| Resultado da negociação | 5 | Lucas | ✅ | `POST /decisoes/{id}/resultado` (colunas em `decisoes`) |
| Eventos de auditoria | 4 | Lucas | ✅ | `POST /eventos` + eventos automáticos abriu_caso, viu_recomendacao, abriu_documento |
| Dashboard de aderência (números) | 4 | Lucas | ✅ | `GET /dashboard/aderencia` → `services/metricas.py` (por escritório, advogado, semana, justificativas, % sem ver recomendação) |
| Dashboard de efetividade (números) | 5 | Lucas | ✅ | `GET /dashboard/efetividade` (aceite real vs hipótese, desconto, economia realizada, backtest da política ativa, ModeloInfo) |
| Políticas: simular, publicar, versões | 1, 5 | Lucas | ✅ | `routers/politicas.py`, `services/backtest.py`; `ativar` grava `resumo_backtest`; `/api/internal/reload-historico` |
| Link mágico `/demo` para a banca | 3 | Lucas | ✅ | `GET /api/demo?t=` reserva caso livre da Banca Demo por 15 min, rate limit 20/min |
| Front básico: login, casos, caso, casca do painel, política, aprovações | 3, 4, 5 | Lucas | ✅ | `pages/{Login,advogado/*,gestor/*}.tsx`; painel faz poll de 5 s; política simula com debounce de 300 ms e publica com diff; P4/P5 polem a partir daqui |
| Compose, Caddy, deploy VPS, standby homelab, backup | — | Lucas | ⬜ | `infra/`, `Makefile` |
| Clone limpo sobe sem dados da Enter: modelo exportado, resumo do backtest, processos sintéticos nossos | — | Lucas; P1 exporta o modelo | 🔧 | `data/exemplos/sinteticos.csv` ✅ e seed ✅; modelo exportado em `src/model/artifacts/` pendente (P1) |
| Modelo XGBoost + scores OOF do histórico | 1, 2 | P1 | ⬜ | `src/model` |
| Extração LLM dos PDFs + sinais de alerta | 1, 3 | P3 | ⬜ | `src/extractor` |
| Análise e minutas em linguagem jurídica | 3 | P3 | ⬜ | `src/extractor` |
| Portal do advogado polido + vídeo | 3 | P4 | ⬜ | `pages/advogado`, `docs/video.*` |
| Gráficos do painel e tela de política | 4, 5 | P5 | ⬜ | `pages/gestor` |
| Slides, README e SETUP finais | — | P5 | ⬜ | `docs/`, `SETUP.md`, `README.md` |
