# Backtest da política `2026.09.12-v1` (modelo `logit-60000-20260912`)

Base: **60,000 processos** (base completa da Enter).
Custos reais de defender usam o resultado que de fato ocorreu (condenação, êxito, extinção); ver premissas em `docs/premissas.md`.

## Modelo de probabilidade de perda (out-of-fold, 5 folds)
- AUC **0.923** · Brier 0.093 · acurácia@0,5 87.2% · ECE **0.003** · taxa de perda 30.4%

| p prevista | n | prevista média | observada |
|---|---|---|---|
| -0.0–0.1 | 29,363 | 0.042 | 0.041 |
| 0.1–0.2 | 7,541 | 0.142 | 0.145 |
| 0.2–0.3 | 2,552 | 0.246 | 0.254 |
| 0.3–0.4 | 849 | 0.351 | 0.326 |
| 0.4–0.5 | 2,628 | 0.455 | 0.456 |
| 0.5–0.6 | 2,662 | 0.548 | 0.558 |
| 0.6–0.7 | 1,637 | 0.649 | 0.631 |
| 0.7–0.8 | 3,242 | 0.753 | 0.748 |
| 0.8–0.9 | 3,028 | 0.847 | 0.847 |
| 0.9–1.0 | 6,498 | 0.973 | 0.974 |

![calibracao](calibracao.png)

## Financeiro
- Condenações históricas: **R$ 193.0M** (R$ 3,216 por caso; ~R$ 16.1M/mês em 5 mil casos)
- Custo real de **defender tudo** (condenação + honorários + custas + tempo + escritório): **R$ 342.9M**
- Custo de **acordar tudo** no alvo (curva de aceite): R$ 246.6M
- Custo sob a **política** (curva de aceite): **R$ 236.7M** → economia **R$ 106.3M (31.0%)**, acordo em 36.2% dos casos

### Sensibilidade (economia vs. defender tudo)
| taxa de aceite | oferta × | custo | economia | % |
|---|---|---|---|---|
| 0.5 | 0.8 | R$ 270.7M | R$ 72.3M | 21.1% |
| 0.5 | 1.0 | R$ 283.4M | R$ 59.6M | 17.4% |
| 0.5 | 1.2 | R$ 296.0M | R$ 46.9M | 13.7% |
| 0.6 | 0.8 | R$ 254.9M | R$ 88.0M | 25.7% |
| 0.6 | 1.0 | R$ 270.1M | R$ 72.8M | 21.2% |
| 0.6 | 1.2 | R$ 285.3M | R$ 57.6M | 16.8% |
| 0.7 | 0.8 | R$ 239.2M | R$ 103.8M | 30.3% |
| 0.7 | 1.0 | R$ 256.9M | R$ 86.0M | 25.1% |
| 0.7 | 1.2 | R$ 274.7M | R$ 68.3M | 19.9% |
| 0.8 | 0.8 | R$ 223.4M | R$ 119.5M | 34.9% |
| 0.8 | 1.0 | R$ 243.7M | R$ 99.2M | 28.9% |
| 0.8 | 1.2 | R$ 264.0M | R$ 79.0M | 23.0% |
| curva | 0.8 | R$ 216.1M | R$ 126.8M | 37.0% |
| curva | 1.0 | R$ 236.7M | R$ 106.3M | 31.0% |
| curva | 1.2 | R$ 257.2M | R$ 85.7M | 25.0% |

![sensibilidade](sensibilidade.png)

### Faixas
| faixa | casos | % casos | p perda prevista | perda real | condenação real | custo real defesa |
|---|---|---|---|---|---|---|
| amarela | 11,289 | 18.8% | 35.7% | 35.7% | R$ 41.3M | R$ 71.6M |
| verde | 34,286 | 57.1% | 5.4% | 5.4% | R$ 19.1M | R$ 68.0M |
| vermelha | 14,425 | 24.0% | 85.9% | 85.8% | R$ 132.5M | R$ 203.3M |

![faixas](faixas.png)

## Subsídios
| documento | perda quando presente | perda quando ausente | Δ p.p. |
|---|---|---|---|
| Contrato | 12.7% | 75.3% | +62.6 |
| Extrato | 18.8% | 81.7% | +62.9 |
| Comprovante de crédito (BACEN) | 19.9% | 46.7% | +26.8 |
| Dossiê | 30.5% | 30.4% | -0.0 |
| Demonstrativo de evolução da dívida | 27.8% | 39.4% | +11.7 |
| Laudo referenciado | 30.5% | 30.3% | -0.2 |

Valor da informação — custo esperado de litigar evitável se o subsídio ausente fosse recuperado:
| documento | casos sem | ganho total | por caso |
|---|---|---|---|
| Contrato | 17,017 | R$ 110.1M | R$ 6,469 |
| Extrato | 11,105 | R$ 62.0M | R$ 5,579 |
| Comprovante de crédito (BACEN) | 23,586 | R$ 46.7M | R$ 1,981 |
| Demonstrativo de evolução da dívida | 13,785 | R$ 10.4M | R$ 751 |

![subsidios](subsidios.png)
