# Features

Estado: ✅ pronta · 🔧 em andamento · ⬜ planejada. Edite a linha; não adicione histórico.

| Feature | Req | Dono | Estado | Onde |
|---|---|---|---|---|
| Regras de colaboração e memory-bank | — | Lucas | ✅ | `CLAUDE.md`, `memory-bank/` |
| CI de PR: commits, memory-bank, segredos, testes por componente | — | Lucas | ✅ | `.github/workflows/ci.yml`, `scripts/`, `Makefile` |
| Parsing dos CSVs da Enter e UF por número CNJ | — | Lucas | ✅ | `src/core/core/colunas.py`, `src/core/core/cnj.py` |
| Contratos P1/P3 e stubs | — | Lucas | ⬜ | `src/core/core/{caso,modelo,docs}.py`, `src/api/app/stubs.py` |
| Política de custo esperado e backtest | 1, 2, 5 | Lucas; P1 calibra | ⬜ | `src/core/core/politica.py` |
| Auth por cookie, papéis advogado/gestor | 3 | Lucas | ⬜ | `src/api/app/auth.py` |
| Jobs: seed, load-historico, ingest, seed-demo, reset-demo | — | Lucas | ⬜ | `src/api/app/cli.py` |
| Lista e detalhe de processos, arquivos | 3 | Lucas | ⬜ | `routers/processos.py`, `routers/files.py`, `pages/advogado` |
| Recomendação gravada sob a política ativa | 1, 2, 4 | Lucas | ⬜ | `services/recomendacao.py` |
| Decisão com aderência, justificativa e aprovação | 4 | Lucas | ⬜ | `routers/processos.py` |
| Resultado da negociação | 5 | Lucas | ⬜ | `routers/processos.py` |
| Eventos de auditoria | 4 | Lucas | ⬜ | `routers/processos.py` |
| Dashboard de aderência (números) | 4 | Lucas | ⬜ | `services/metricas.py` |
| Dashboard de efetividade (números) | 5 | Lucas | ⬜ | `services/metricas.py` |
| Políticas: simular, publicar, versões | 1, 5 | Lucas | ⬜ | `routers/politicas.py`, `services/backtest.py` |
| Link mágico `/demo` para a banca | 3 | Lucas | ⬜ | `routers/demo.py` |
| Front básico: login, casos, caso, casca do painel, política, aprovações | 3, 4, 5 | Lucas | ⬜ | `src/web/src/pages` |
| Compose, Caddy, deploy VPS, standby homelab, backup | — | Lucas | ⬜ | `infra/`, `Makefile` |
| Modelo XGBoost + scores OOF do histórico | 1, 2 | P1 | ⬜ | `src/model` |
| Extração LLM dos PDFs + sinais de alerta | 1, 3 | P3 | ⬜ | `src/extractor` |
| Análise e minutas em linguagem jurídica | 3 | P3 | ⬜ | `src/extractor` |
| Portal do advogado polido + vídeo | 3 | P4 | ⬜ | `pages/advogado`, `docs/video.*` |
| Gráficos do painel e tela de política | 4, 5 | P5 | ⬜ | `pages/gestor` |
| Slides, README e SETUP finais | — | P5 | ⬜ | `docs/`, `SETUP.md`, `README.md` |
