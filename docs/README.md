# docs/

Documentação e artefatos de entrega do Grupo 3. Como rodar a solução está no [`README.md`](../README.md) e no
[`SETUP.md`](../SETUP.md).

| Arquivo | O que tem |
|---|---|
| [`relatorio.md`](relatorio.md) | relatório técnico: a política, os números do backtest, o que os dados dizem, as decisões, as limitações e os próximos passos |
| [`politica.md`](politica.md) | a política de acordos em linguagem jurídica |
| [`premissas.md`](premissas.md) | cada número usado: o que é observado na base e o que é premissa declarada |
| [`video.md`](video.md) | roteiro do vídeo de 2 min do ponto de vista do advogado: checklist de gravação, falas cronometradas e o que fazer fora do vídeo |
| [`painel_gestor_spec.md`](painel_gestor_spec.md) | especificação do painel do gestor: aderência, efetividade e parecer consultivo da IA |
| [`backtest/resumo.md`](backtest/resumo.md) | replay da política nos 60 mil casos, com baselines, sensibilidade e gráficos (`make backtest`) |
| [`modelo/comparacao.md`](modelo/comparacao.md) | comparação de modelos de probabilidade de perda pelo custo de decisão (`make compare-models`) |
| [`analises/resumo.md`](analises/resumo.md) | análises e figuras da demonstração: severidade por UF, fronteira da política, valor de instruir (`make analises`) |
| [`extractor/benchmark.md`](extractor/benchmark.md) · [`extractor/benchmark-llm.md`](extractor/benchmark-llm.md) | compressão do texto dos PDFs antes do LLM e comparação dos modelos na extração |

Os arquivos sob `backtest/`, `modelo/`, `analises/` e `extractor/` são gerados por script — edite o código, não o
resultado. A apresentação final e o vídeo de até 2 minutos entram aqui na entrega.
