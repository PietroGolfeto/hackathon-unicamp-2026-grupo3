# Comparação de modelos de P(perda) pelo custo de decisão out-of-fold

Base: 59,720 sentenças (280 acordos históricos excluídos), 5 folds estratificados (semente 42). Regra comum: acordo quando EV_acordo < EV_defesa com oferta fixa de 30% do VC e aceite 65%; custos de `policy.yaml`. Só a probabilidade muda entre linhas.

Defender tudo: **R$ 340.8M** · Oráculo (resultado conhecido): **R$ 209.8M** → ganho máximo possível R$ 131.0M.

| modelo | AUC | log-loss | Brier | ECE | custo OOF | % acordo | captura do ganho máximo |
|---|---|---|---|---|---|---|---|
| Logística 6 docs + sub + UF (v1) | 0.9226 | 0.3079 | 0.0929 | 0.0029 | R$ 242.7M | 36.1% | 74.9% |
| Logística 4 docs + sub + UF (v2, escolhida) | 0.9226 | 0.3079 | 0.0929 | 0.0031 | R$ 242.7M | 36.1% | 74.9% |
| … sem UF | 0.9187 | 0.3121 | 0.0941 | 0.0023 | R$ 243.3M | 35.2% | 74.4% |
| … + valor da causa | 0.9226 | 0.3079 | 0.0929 | 0.0033 | R$ 242.6M | 36.1% | 74.9% |
| … + interações docs×docs e sub×docs | 0.9226 | 0.3079 | 0.0929 | 0.0028 | R$ 242.6M | 36.3% | 74.9% |
| … saturada sub×docs (32 células) + UF | 0.9225 | 0.3083 | 0.0930 | 0.0019 | R$ 242.7M | 36.3% | 74.8% |
| … UF encolhida (colunas × 0.3) | 0.9226 | 0.3079 | 0.0929 | 0.0028 | R$ 242.7M | 36.0% | 74.9% |
| HistGradientBoosting (6 docs + sub + UF + VC) | 0.9217 | 0.3099 | 0.0935 | 0.0056 | R$ 243.0M | 36.2% | 74.6% |
| Tabela de segmentos k=20 (estimador da v1) | 0.9206 | 0.3120 | 0.0939 | 0.0044 | R$ 243.1M | 36.5% | 74.6% |
| Células brutas UF×sub×4 docs | 0.9173 | 0.3241 | 0.0955 | 0.0072 | R$ 243.4M | 36.3% | 74.3% |
| Engine v1: média(tabela, logística 6 docs) | 0.9221 | 0.3089 | 0.0932 | 0.0027 | R$ 242.8M | 36.3% | 74.8% |

Amplitude entre o melhor (… + interações docs×docs e sub×docs) e o pior (Células brutas UF×sub×4 docs): **R$ 0.8M** (0.2% do custo de defender tudo). A escolha do modelo não é onde está o dinheiro; a estrutura de custos, o valor da informação e a oferta são.
