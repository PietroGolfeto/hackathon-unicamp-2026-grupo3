# Backtest da política `2026.09.12-v2` (modelo `logit-60000-20260912`)

Base: **60,000 processos** (base completa da Enter).
Custos reais de defender usam o resultado que de fato ocorreu (condenação, êxito, extinção); ver premissas em `docs/premissas.md`.

## Modelo de probabilidade de perda (out-of-fold, 5 folds)
- AUC **0.923** · Brier 0.093 · acurácia@0,5 87.3% · ECE **0.003** · taxa de perda 30.1%

| p prevista | n | prevista média | observada |
|---|---|---|---|
| -0.0–0.1 | 29,745 | 0.042 | 0.041 |
| 0.1–0.2 | 7,102 | 0.142 | 0.146 |
| 0.2–0.3 | 2,608 | 0.244 | 0.249 |
| 0.3–0.4 | 878 | 0.354 | 0.322 |
| 0.4–0.5 | 2,653 | 0.455 | 0.460 |
| 0.5–0.6 | 2,606 | 0.548 | 0.559 |
| 0.6–0.7 | 1,646 | 0.651 | 0.628 |
| 0.7–0.8 | 3,134 | 0.752 | 0.749 |
| 0.8–0.9 | 3,009 | 0.846 | 0.846 |
| 0.9–1.0 | 6,339 | 0.973 | 0.975 |

![calibracao](calibracao.png)

## Financeiro
- Condenações históricas: **R$ 193.0M** (R$ 3,216 por caso; ~R$ 16.1M/mês em 5 mil casos)
- Custo real de **defender tudo** (condenação + honorários + custas + tempo + escritório): **R$ 342.9M**
- Custo de **acordar tudo** no alvo (curva de aceite): R$ 246.7M
- Custo sob a **política** (curva de aceite): **R$ 236.8M** → economia **R$ 106.2M (31.0%)**, acordo em 36.3% dos casos
- Probabilidade usada no replay: **out-of-fold** (5 folds; cada caso pontuado por um modelo que não o viu); acordos históricos (280) entram com o valor que de fato pagaram.

### Baselines (mesmos custos; só a regra de decisão muda)
| regra | custo | economia | % | % acordo | captura do ganho máximo |
|---|---|---|---|---|---|
| Defender tudo (o que aconteceu) | R$ 342.9M | R$ 0 | 0.0% | 0.0% | 0% |
| Acordar tudo a 30% do VC (aceite 65%) | R$ 313.3M | R$ 29.6M | 8.6% | 100.0% | 20% |
| Heurística: sem contrato → acordo | R$ 260.7M | R$ 82.2M | 24.0% | 28.4% | 54% |
| Heurística: sem contrato e sem extrato → acordo | R$ 297.6M | R$ 45.3M | 13.2% | 10.8% | 30% |
| Limiar fixo p_perda > 0.60 (3 grupos da UFMG), oferta 30% | R$ 257.9M | R$ 85.1M | 24.8% | 23.8% | 56% |
| Política EV (p OOF, escada, aceite fixo 65%) | R$ 263.6M | R$ 79.3M | 23.1% | 36.3% | 52% |
| Política EV (p OOF, escada + curva de aceite) | R$ 236.8M | R$ 106.2M | 31.0% | 36.3% | 70% |
| Oráculo: resultado conhecido, mesma escada (teto teórico) | R$ 191.1M | R$ 151.9M | 44.3% | 30.4% | 100% |

Leitura: o ganho vem de decidir pelo custo total de litigar, não de prever melhor a sentença; a política captura a maior parte do que um oráculo capturaria.

![baselines](baselines.png)

### Banda do número (variação amostral)
- Economia por fold: 30.7% · 30.9% · 31.7% · 30.9% · 31.2% → média **31.1% ± 0.4 p.p.**
- Bootstrap por caso (200×): IC95 **30.6% – 31.4%**
- O lado *acordo* é hipótese (curva de aceite): a banda mede só a variação amostral do modelo, não a incerteza sobre o aceite — ver sensibilidade.

### Ponto de indiferença (breakeven) e decisões sensíveis
- p\* médio (p_perda em que acordar no alvo da escada custa o mesmo que defender): **0.47** (p5 0.24 · p95 0.84); casos cujo IC95 de p cruza p\*: **2.2%** (vão para revisão)

### Sensibilidade ao aceite e ao valor da oferta (economia vs. defender tudo)
| taxa de aceite | oferta × | custo | economia | % |
|---|---|---|---|---|
| 0.5 | 0.8 | R$ 270.7M | R$ 72.2M | 21.1% |
| 0.5 | 1.0 | R$ 283.4M | R$ 59.5M | 17.4% |
| 0.5 | 1.2 | R$ 296.1M | R$ 46.8M | 13.6% |
| 0.6 | 0.8 | R$ 255.0M | R$ 88.0M | 25.7% |
| 0.6 | 1.0 | R$ 270.2M | R$ 72.7M | 21.2% |
| 0.6 | 1.2 | R$ 285.5M | R$ 57.5M | 16.8% |
| 0.7 | 0.8 | R$ 239.2M | R$ 103.7M | 30.2% |
| 0.7 | 1.0 | R$ 257.0M | R$ 85.9M | 25.1% |
| 0.7 | 1.2 | R$ 274.8M | R$ 68.1M | 19.9% |
| 0.8 | 0.8 | R$ 223.5M | R$ 119.5M | 34.8% |
| 0.8 | 1.0 | R$ 243.8M | R$ 99.1M | 28.9% |
| 0.8 | 1.2 | R$ 264.2M | R$ 78.8M | 23.0% |
| curva | 0.8 | R$ 216.1M | R$ 126.8M | 37.0% |
| curva | 1.0 | R$ 236.8M | R$ 106.2M | 31.0% |
| curva | 1.2 | R$ 257.4M | R$ 85.6M | 24.9% |

![sensibilidade](sensibilidade.png)

### Sensibilidade à âncora da curva de aceite (s50 = fração do VC em que 50% aceitam)
| s50 | custo da política | economia | % acordo |
|---|---|---|---|
| 0.25 | R$ 223.5M | 34.8% | 40.1% |
| 0.30 | R$ 236.8M | 31.0% | 36.3% |
| 0.40 | R$ 261.1M | 23.9% | 33.5% |
| 0.50 | R$ 282.7M | 17.6% | 31.3% |

### Sensibilidade aos custos de litigar (defender tudo e política recalculados)
| cenário | defender tudo | política | economia | % acordo | p\* médio |
|---|---|---|---|---|---|
| Base (vara: sucumbência 15%, custas 2%, 18 meses) | R$ 342.9M | R$ 236.8M | 31.0% | 36.3% | 0.47 |
| Escritório × 0,5 | R$ 306.9M | R$ 210.8M | 31.3% | 35.1% | 0.56 |
| Escritório × 1,5 | R$ 378.9M | R$ 262.0M | 30.9% | 39.3% | 0.36 |
| Sucumbência 10% | R$ 331.4M | R$ 233.5M | 29.5% | 36.0% | 0.49 |
| Sucumbência 20% | R$ 354.5M | R$ 240.0M | 32.3% | 36.8% | 0.45 |
| Tempo 10 meses (fator 1,10) | R$ 322.6M | R$ 230.9M | 28.4% | 35.8% | 0.51 |
| Tempo 22 meses (fator 1,25) | R$ 353.7M | R$ 239.7M | 32.2% | 36.7% | 0.45 |
| Sem custas | R$ 337.5M | R$ 235.2M | 30.3% | 36.2% | 0.48 |
| Cenário JEC (Lei 9.099: sem custas nem sucumbência em 1º grau, 9 meses) | R$ 283.1M | R$ 218.1M | 22.9% | 34.7% | 0.60 |

### Instruir antes de acordar (valor esperado da informação)
- Casos em que vale pedir contrato e/ou extrato antes de propor acordo: **20,176 (33.6% dos casos; 93% dos acordos)**; EVSI total R$ 50.5M — hipótese: q_d = P(doc | outros docs) é a chance de o back-office localizar o documento.
| chance de localizar (× q_d) | casos instruir | % | EVSI total | EVSI médio |
|---|---|---|---|---|
| × 0.5 | 14,335 | 23.9% | R$ 16.9M | R$ 1,178 |
| × 0.75 | 18,311 | 30.5% | R$ 32.4M | R$ 1,771 |
| × 1.0 | 20,176 | 33.6% | R$ 50.5M | R$ 2,502 |

### Por UF
| UF | % acordo | p\* médio | severidade (cond/VC) | perda real | defender tudo | política | economia |
|---|---|---|---|---|---|---|---|
| AP | 60% | 0.32 | 0.83 | 48% | R$ 22.0M | R$ 12.5M | 42.9% |
| AM | 61% | 0.33 | 0.83 | 48% | R$ 22.2M | R$ 12.9M | 42.1% |
| BA | 43% | 0.39 | 0.79 | 35% | R$ 16.3M | R$ 10.1M | 37.9% |
| GO | 44% | 0.42 | 0.72 | 38% | R$ 16.0M | R$ 10.5M | 34.5% |
| RS | 44% | 0.41 | 0.72 | 38% | R$ 15.9M | R$ 10.6M | 33.6% |
| RJ | 40% | 0.45 | 0.68 | 35% | R$ 14.2M | R$ 9.8M | 31.3% |
| ES | 41% | 0.46 | 0.68 | 33% | R$ 13.9M | R$ 9.7M | 30.6% |
| AL | 35% | 0.48 | 0.68 | 31% | R$ 13.1M | R$ 9.1M | 30.3% |
| PE | 36% | 0.47 | 0.68 | 31% | R$ 13.4M | R$ 9.4M | 29.9% |
| SP | 36% | 0.47 | 0.69 | 31% | R$ 13.1M | R$ 9.2M | 29.8% |
| DF | 40% | 0.46 | 0.68 | 33% | R$ 13.6M | R$ 9.6M | 29.5% |
| MG | 36% | 0.48 | 0.68 | 30% | R$ 12.7M | R$ 8.9M | 29.4% |
| PA | 33% | 0.49 | 0.68 | 28% | R$ 12.1M | R$ 8.6M | 28.5% |
| SE | 33% | 0.50 | 0.67 | 29% | R$ 12.2M | R$ 8.7M | 28.5% |
| RO | 30% | 0.49 | 0.69 | 26% | R$ 11.4M | R$ 8.1M | 28.4% |
| PB | 33% | 0.48 | 0.68 | 29% | R$ 12.1M | R$ 8.7M | 28.4% |
| AC | 32% | 0.47 | 0.69 | 28% | R$ 12.0M | R$ 8.6M | 28.2% |
| SC | 32% | 0.48 | 0.69 | 27% | R$ 12.0M | R$ 8.6M | 28.2% |
| CE | 33% | 0.48 | 0.68 | 28% | R$ 12.2M | R$ 8.8M | 28.0% |
| PR | 31% | 0.49 | 0.68 | 26% | R$ 11.2M | R$ 8.2M | 27.0% |
| TO | 29% | 0.49 | 0.69 | 25% | R$ 11.2M | R$ 8.2M | 26.9% |
| PI | 28% | 0.51 | 0.69 | 23% | R$ 10.6M | R$ 7.8M | 26.8% |
| RN | 28% | 0.50 | 0.68 | 24% | R$ 11.0M | R$ 8.2M | 26.1% |
| MS | 30% | 0.55 | 0.61 | 25% | R$ 10.0M | R$ 7.6M | 24.4% |
| MT | 29% | 0.55 | 0.61 | 24% | R$ 9.7M | R$ 7.6M | 22.0% |
| MA | 26% | 0.58 | 0.61 | 21% | R$ 8.9M | R$ 6.9M | 21.7% |

### Faixas
| faixa | casos | % casos | p perda prevista | perda real | condenação real | custo real defesa |
|---|---|---|---|---|---|---|
| amarela | 11,220 | 18.7% | 35.9% | 36.5% | R$ 42.1M | R$ 72.6M |
| verde | 34,471 | 57.5% | 5.3% | 5.5% | R$ 19.3M | R$ 68.5M |
| vermelha | 14,309 | 23.8% | 86.0% | 85.9% | R$ 131.6M | R$ 201.9M |

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

Ganho se encontrar — queda do custo esperado de litigar se o subsídio ausente fosse recuperado (limite superior do valor da informação):
| documento | casos sem | ganho total | por caso |
|---|---|---|---|
| Contrato | 17,017 | R$ 111.4M | R$ 6,549 |
| Extrato | 11,105 | R$ 62.9M | R$ 5,664 |
| Comprovante de crédito (BACEN) | 23,586 | R$ 47.4M | R$ 2,008 |
| Demonstrativo de evolução da dívida | 13,785 | R$ 10.6M | R$ 770 |

![subsidios](subsidios.png)
