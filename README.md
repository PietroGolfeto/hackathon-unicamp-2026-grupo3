# Política de Acordos — Banco Unicamp · Grupo 3 (Hackathon Enter/Unicamp 2026)

> ~5 mil ações por mês alegam "não reconheço este empréstimo". Para cada uma, o advogado externo decide: **defender ou
> propor acordo?** Nossa resposta: uma política de acordos que é um **sistema de decisão econômico** — probabilidade
> calibrada de perder × custo total de litigar, comparada ao custo de acordar — com **IA nas pontas** (ler autos e
> subsídios, cruzar fatos, redigir) e **estatística determinística no centro** (decidir e precificar), fechada por um
> **monitoramento que aprende** (aderência com taxonomia de desvio, curva de aceite por experimento). Custo por caso:
> centavos. Decisão: < 1 ms. Tudo reproduzível na base de 60 mil sentenças.

Este README consolida **todas as decisões** do grupo e o que aprendemos com os dados e com as 10 submissões da edição
UFMG. Documentos de apoio: [`docs/politica.md`](docs/politica.md) (política em linguagem jurídica),
[`docs/premissas.md`](docs/premissas.md) (cada número: observado × premissa), [`docs/backtest/resumo.md`](docs/backtest/resumo.md)
(números gerados por script), [`SETUP.md`](SETUP.md) (como rodar).

---

## 1. A política em uma tela (para o jurídico)

| Faixa | Quando | Ação |
|---|---|---|
| 🟢 **Verde — defender** | Contrato **e** extrato presentes e consistentes (crédito na conta do autor). Perda < 15%. **57% dos casos, 20% do custo** | Contestação padrão; se a petição contradiz o extrato, alegar má-fé |
| 🟡 **Amarela — instruir antes de decidir** | Falta contrato **ou** extrato, mas recuperá-lo derruba o custo esperado em > 10% do valor da causa. **19% dos casos** | Solicitar o subsídio ao banco (5 dias). Veio → reavaliar. Não veio → acordar |
| 🔴 **Vermelha — acordar já** | Perda > 60% **ou** sinal grave (crédito em conta de terceiro, biometria ausente em canal digital, documento inconsistente). **24% dos casos, 59% do custo** | Propor na 1ª oportunidade: cancelamento + baixa do saldo + devolução das parcelas + indenização, seguindo a escada **abertura / alvo / teto** |

Regras de ouro: nunca acima do teto (90% do custo esperado de litigar); política não é divulgada (23% de extinções
sugerem litigância em massa); toda decisão é registrada contra a recomendação vista; documento que não prova o que
deveria não conta. Texto completo em [`docs/politica.md`](docs/politica.md).

**Potencial financeiro** (backtest com resultados reais dos 60 mil casos, `make backtest`):

| Cenário | Custo total | Economia vs. defender tudo |
|---|---|---|
| Defender tudo (o que acontece hoje): condenação R$ 193M + honorários + custas + correção + escritório | **R$ 342,9M** | — |
| Acordar tudo no alvo | R$ 246,6M | R$ 96M (28%) |
| **Política (acordo em 36% dos casos)** | **R$ 236,7M** | **R$ 106M (31%)** |
| Política com aceite fixo em 50% / 80% | R$ 283M / R$ 244M | R$ 60M (17%) / R$ 99M (29%) |

Ordem de grandeza: **R$ 5–9 milhões por mês** em 5 mil casos. Sensibilidade completa (aceite × valor da oferta × custos)
em `docs/backtest/`. Todos os custos além da condenação são premissas declaradas e ajustáveis em
[`policy.yaml`](src/enteros/policy/policy.yaml).

### Números completos do backtest

<!-- backtest:inicio -->
_Bloco gerado por `make backtest`; não edite à mão._

### Backtest da política `2026.09.12-v2` (modelo `logit-60000-20260912`)

Base: **60,000 processos** (base completa da Enter).
Custos reais de defender usam o resultado que de fato ocorreu (condenação, êxito, extinção); ver premissas em `docs/premissas.md`.

#### Modelo de probabilidade de perda (out-of-fold, 5 folds)
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

![calibracao](docs/backtest/calibracao.png)

#### Financeiro
- Condenações históricas: **R$ 193.0M** (R$ 3,216 por caso; ~R$ 16.1M/mês em 5 mil casos)
- Custo real de **defender tudo** (condenação + honorários + custas + tempo + escritório): **R$ 342.9M**
- Custo de **acordar tudo** no alvo (curva de aceite): R$ 246.7M
- Custo sob a **política** (curva de aceite): **R$ 236.8M** → economia **R$ 106.2M (31.0%)**, acordo em 36.3% dos casos
- Probabilidade usada no replay: **out-of-fold** (5 folds; cada caso pontuado por um modelo que não o viu); acordos históricos (280) entram com o valor que de fato pagaram.

##### Baselines (mesmos custos; só a regra de decisão muda)
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

![baselines](docs/backtest/baselines.png)

##### Banda do número (variação amostral)
- Economia por fold: 30.7% · 30.9% · 31.7% · 30.9% · 31.2% → média **31.1% ± 0.4 p.p.**
- Bootstrap por caso (200×): IC95 **30.6% – 31.4%**
- O lado *acordo* é hipótese (curva de aceite): a banda mede só a variação amostral do modelo, não a incerteza sobre o aceite — ver sensibilidade.

##### Ponto de indiferença (breakeven) e decisões sensíveis
- p\* médio (p_perda em que acordar no alvo da escada custa o mesmo que defender): **0.47** (p5 0.24 · p95 0.84); casos cujo IC95 de p cruza p\*: **2.2%** (vão para revisão)

##### Sensibilidade ao aceite e ao valor da oferta (economia vs. defender tudo)
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

![sensibilidade](docs/backtest/sensibilidade.png)

##### Sensibilidade à âncora da curva de aceite (s50 = fração do VC em que 50% aceitam)
| s50 | custo da política | economia | % acordo |
|---|---|---|---|
| 0.25 | R$ 223.5M | 34.8% | 40.1% |
| 0.30 | R$ 236.8M | 31.0% | 36.3% |
| 0.40 | R$ 261.1M | 23.9% | 33.5% |
| 0.50 | R$ 282.7M | 17.6% | 31.3% |

##### Sensibilidade aos custos de litigar (defender tudo e política recalculados)
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

##### Instruir antes de acordar (valor esperado da informação)
- Casos em que vale pedir contrato e/ou extrato antes de propor acordo: **20,176 (33.6% dos casos; 93% dos acordos)**; EVSI total R$ 50.5M — hipótese: q_d = P(doc | outros docs) é a chance de o back-office localizar o documento.
| chance de localizar (× q_d) | casos instruir | % | EVSI total | EVSI médio |
|---|---|---|---|---|
| × 0.5 | 14,335 | 23.9% | R$ 16.9M | R$ 1,178 |
| × 0.75 | 18,311 | 30.5% | R$ 32.4M | R$ 1,771 |
| × 1.0 | 20,176 | 33.6% | R$ 50.5M | R$ 2,502 |

##### Por UF
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

##### Faixas
| faixa | casos | % casos | p perda prevista | perda real | condenação real | custo real defesa |
|---|---|---|---|---|---|---|
| amarela | 11,220 | 18.7% | 35.9% | 36.5% | R$ 42.1M | R$ 72.6M |
| verde | 34,471 | 57.5% | 5.3% | 5.5% | R$ 19.3M | R$ 68.5M |
| vermelha | 14,309 | 23.8% | 86.0% | 85.9% | R$ 131.6M | R$ 201.9M |

![faixas](docs/backtest/faixas.png)

#### Subsídios
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

![subsidios](docs/backtest/subsidios.png)
<!-- backtest:fim -->

---

## 2. O que os dados dizem (60.000 sentenças, 2 abas, join 1:1)

| Achado | Número | Consequência na política |
|---|---|---|
| **Contrato e extrato decidem** | perda 13% × 75% (contrato); 19% × 82% (extrato) | são os dois documentos "críticos"; a faixa verde exige ambos |
| Comprovante BACEN e demonstrativo ajudam menos | 20% × 47%; 28% × 39% | pesam no modelo, não definem faixa |
| **Dossiê e laudo não movem nada** | 30,5% × 30,4%; 30,5% × 30,3% | não entram na faixa; insight para o banco: perícia terceirizada não compra êxito |
| Nº de subsídios → êxito | 0→0% · 1→3% · 2→13% · 3→34% · 4→64% · 5→87% · 6→96% | monotônico; o engine garante que mais docs nunca aumenta o risco |
| Sub-assunto | Golpe perde 36%; Genérico 17% | feature |
| UF | AP/AM perdem ~48% e pagam 84% do pedido; MA perde 21% e paga 60% | feature + razão de condenação por UF |
| Valor da causa | **não** altera a probabilidade de perder (69–70% em todas as faixas) | condenação escala linearmente com o VC |
| Condenação dado perda | 70% do VC em média (p20 0,55 · p50 0,74 · p80 0,86) | quantis para a escada |
| Acordos históricos | 280, fechados a 20–40% do VC (mediana 29%), 74% sem contrato | âncora da curva de aceite |
| Extinção | 23% dos casos, independente de docs | mantida no backtest como defesa vencida com condenação zero; sinal de litigância predatória |
| Modelo logístico (docs + sub + UF) | **AUC 0,923 · Brier 0,093 · ECE 0,003** (out-of-fold, 5 folds) | calibração quase perfeita → o valor esperado é confiável |

### Os dois processos exemplo são extremos deliberados

| | Caso 01 — São Luís/MA | Caso 02 — Manaus/AM |
|---|---|---|
| Canal | correspondente por telefone, assinatura manuscrita | app mobile, biometria |
| Subsídios | 6/6; dossiê conforme (assinatura 91%, liveness 97%) | 3/6: sem contrato, sem extrato, sem dossiê |
| Prova de proveito | extrato: crédito R$ 5 mil + TED para conta própria + PIX + saque em São Luís | crédito em conta da **Caixa** que o autor diz não ter; laudo admite **liveness não localizado** |
| Autor | idosa, pede R$ 15 mil de dano moral, VC R$ 20 mil | idoso, BO + BACEN, pede R$ 18 mil, VC R$ 25 mil |
| Engine | **DEFESA** · perda 0,9% · a petição diz "jamais utilizou os valores" — o extrato prova o contrário | **ACORDO** · perda 97% · litigar custa ≈ R$ 30 mil · escada R$ 9,0 mil / **R$ 11,25 mil** / R$ 17,5 mil (devolução R$ 1.440 + baixa R$ 2.748 + indenização) |

---

## 3. O que os 10 grupos da UFMG fizeram — e onde ficaram os furos

Tabelas completas por grupo (stack, regra de decisão, fórmula de valor, UI, monitoramento, ideia única, furo) em [`docs/analise_ufmg_2026.md`](docs/analise_ufmg_2026.md).

**Vencedor (Exit.OS, G1)**: XGBoost com limiar fixo 0,60 → depois precifica com banda de quantis empíricos. Venceu pelos
**artefatos concretos por processo** (`Defesa.pdf` gerado por LLM com prompt bem guardado, `Contato.json` com o
advogado adverso extraído dos autos) e por UX memorável (cronômetro, chips de "recibo de leitura"). Sem número
financeiro, sem persistência, não reproduzível. **Pódio (G10)**: infra pesada (Postgres/pgvector/Docker), UX rica
(Central de Evidências, trechos citados, justificativa se delta > 15%), mas a **LLM fazia a conta do valor** e o deck
prometia RAG de 60k que não existia.

Ideias únicas dos demais: G8 apetite de risco como quantil dos 280 acordos + IFP; G2 formulação probabilística limpa
+ economia contrafactual; G3-UFMG matriz UF × nº docs com backtest real + LLM-as-judge; G7 único a modelar aceite do
autor (parâmetros chutados) e otimizar a oferta; G9 registro de premissas H1–H14 com "observado × assumido"; G4
política gerada/criticada/versionada por LLM + regras duras + checagem contrato × depósito; G6 KPIs fatiados por
"seguiu × não seguiu"; G5 score qualitativo da LLM move o limiar + saída "extinção".

**Table stakes** (todos fizeram; não diferencia): custo esperado como framing; 6 flags + UF + sub-assunto; upload →
extração → card com justificativa em linguagem natural; botão de confirmar; dashboard de aderência; dial de apetite.

**Furos que ninguém fechou** (e que atacamos): (1) valor esperado com custo **total** de litigar e limiar derivado da
economia; (2) número financeiro **tirado dos dados por script reproduzível**; (3) **calibração** de verdade; (4)
verificação de **conteúdo** dos documentos e contradições petição × subsídios; (5) dossiê/laudo inúteis + **valor de
recuperar** um subsídio ausente; (6) loop de efetividade com **experimento** para aprender a curva de aceite; (7)
aderência com **taxonomia de desvio**; (8) oferta **decomposta** + escada + mensagem ao adverso; (9) **evals** de LLM;
(10) rodar com um comando, com e sem chave.

---

## 4. Nossos diferenciais (por critério de avaliação)

| # | Diferencial | Critério |
|---|---|---|
| D1 | **Decisão por valor esperado**: `EV_defesa = escritório + p·[cond·(1+honorários)·tempo + custas]` vs `EV_acordo = a·alvo + (1−a)·EV_defesa + op`. O limiar cai da economia, não é 0,60 arbitrário | Leitura do problema · Execução |
| D2 | **Backtest reproduzível** com resultados reais, baselines "defender tudo" e "acordar tudo", sensibilidade e gráficos (`make backtest`) | Potencial financeiro · Execução |
| D3 | **Escada decomposta**: abertura / alvo / teto; alvo = argmin do custo esperado sob curva de aceite (premissa declarada); piso = devolução simples; oferta = cancelamento + baixa + devolução + indenização | Criatividade · Leitura |
| D4 | **Auditoria de conteúdo por IA** (trilha em andamento): titularidade da conta de depósito, TED × valor liberado, liveness, dossiê favorável, contradições da petição. Documento inconsistente é **rebaixado** a ausente pelo engine | Uso de IA · Execução |
| D5 | **Valor da informação**: faixa amarela "instruir antes de acordar"; para o banco, recuperar contratos ausentes evitaria **R$ 110M** de custo esperado; extratos, **R$ 62M**; dossiê/laudo: zero | Leitura do problema |
| D6 | **Monitoramento que aprende** (trilha em andamento): taxonomia de desvio, justificativa por código, scorecard com controle estatístico, funil de negociação, curva de aceite por **bandas de oferta randomizadas** (15% de exploração) → bandit ajusta o alvo | Execução · Uso de IA |
| D7 | **Onde o advogado trabalha**: API `POST /recomendacao` que o EnterOS chamaria + portal completo (`src/web` sobre `src/api`): lista de casos, caso com recomendação, PDFs, decisão com justificativa, resultado; link mágico para a banca. Sem a trilha B, nada é inferido dos documentos: só presença de subsídio, scores e recomendação | Usabilidade · Viabilidade |
| D8 | **Evals e guardrails**: LLM nunca decide dinheiro; saídas validadas por schema; golden set com os 2 casos + sintéticos (trilha em andamento) | Uso de IA |

---

## 5. Registro de decisões (ADR curto)

| # | Decisão | Por quê |
|---|---|---|
| 1 | **Valor esperado em vez de limiar de probabilidade** | 0,60 (usado por 3 grupos) não tem justificativa econômica; o EV torna o limiar função dos custos e explicável ao jurídico |
| 2 | **Regressão logística + tabela de segmentos, não XGBoost** | A base é quase linear em log-odds (AUC 0,923 vs ~0,92 dos XGBoost dos outros grupos); artefato é um JSON de 30 coeficientes, auditável e sem dependência; a tabela de segmentos (831 células com shrinkage) é a política em forma de planilha |
| 3 | **Média entre tabela e logística; intervalo = discordância** | Segmentos raros são suavizados; a discordância vira medida de incerteza mostrada ao advogado |
| 4 | **Dossiê e laudo ficam no modelo mas não definem faixa** | Efeito observado é zero; manter como feature evita "esconder" o dado; a faixa usa só o que o juiz olha |
| 5 | **LLM só nas pontas** (extrair, cruzar fatos, redigir); engine determinístico | Custo (centavos/caso), latência, consistência entre advogados e auditabilidade — G10 perdeu credibilidade deixando a LLM calcular valor |
| 6 | **Extinção mantida no backtest** como defesa vencida com condenação zero | Excluir 23% da base enviesaria o baseline (o vencedor anterior excluiu) |
| 7 | **Curva de aceite é premissa declarada + experimento** | Só há 280 acordos, todos aceitos (viés de seleção); a base não permite estimar a curva — por isso 15% de exploração em bandas para aprendê-la |
| 8 | **Custos de defesa como parâmetros com fonte** (`policy.yaml`, `docs/premissas.md`) | A base não tem honorários, custas nem datas; o jurídico ajusta e o backtest mostra a sensibilidade |
| 9 | **Sinais da IA entram por regra dura, não pelo modelo** | O histórico não tem esses rótulos; vender "conta de terceiro" como feature treinada seria desonesto (Súmula 479 STJ justifica a regra) |
| 10 | **Nenhum dado da Enter no repositório** | Regra da organização; versionamos só modelos em JSON, resumo do backtest e um CSV sintético gerado pelos modelos |
| 11 | **Engine roda sem banco (`make demo`)**; persistência, portal do advogado e painel do gestor vivem na API FastAPI + Postgres + React (`src/api`, `src/web`, `infra/`, um Caddy) | O engine continua reproduzível com um comando; o portal é onde advogado e gestor trabalham e onde a recomendação vista fica gravada |
| 12 | **React + Vite + Tailwind para a tela** (time tem frontend); Streamlit descartado | Foi o que 4 grupos usaram; usabilidade é critério |
| 13 | **Constantes centralizadas** (`config.py`, `policy.yaml`); nomes de domínio em português | Nada hardcoded; política versionada é requisito de aderência |
| 14 | **Limitações declaradas no deck** | G10 perdeu credibilidade prometendo o que não entregou |

---

## 6. Arquitetura

```mermaid
flowchart LR
  subgraph IA["IA nas pontas (trilha B)"]
    A[Autos + Subsídios PDF] --> E[Extratores estruturados<br/>por tipo de documento]
    E --> X[Cruzador de fatos<br/>conta de depósito · TED × contrato · liveness · contradições]
  end
  X -->|CaseFeatures| ENG
  subgraph ENG["Engine determinístico (esta entrega)"]
    M[Tabela de segmentos + logística calibrada<br/>models/*.json] --> P[p_perda]
    R[Razão condenação/VC por UF×sub] --> EV[EV_defesa]
    P --> EV
    Y[policy.yaml<br/>custos · limiares · curva de aceite] --> EV
    EV --> ESC[Escada abertura/alvo/teto<br/>+ decomposição + VOI]
    ESC --> REC[Recomendacao<br/>faixa · decisão · motivos · contribuições]
  end
  REC -->|POST /recomendacao :8001| EXT[Integrações externas<br/>EnterOS]
  REC --> BT[Backtest 60k<br/>docs/backtest]
  M -->|adapter ModeloScores| API
  subgraph PORTAL["Portal e API (src/api + src/web + infra, esta entrega)"]
    API[FastAPI /api :8000<br/>recomendação gravada · decisão · aderência · políticas versionadas] --> DB[(Postgres)]
    API --> UI[Portal do advogado<br/>casos · caso · PDFs · decisão · resultado]
    API --> MON[Painel do gestor<br/>aderência · efetividade · simulação nos 60k · aprovações]
  end
  BT --> MON
```

**Como as duas camadas se encaixam.** O engine é a política de referência e a fonte dos números deste README; o portal é a camada operacional: grava a recomendação exata que o advogado viu (aderência é medida contra ela), exige justificativa no desvio, manda acordos fora da banda para aprovação, registra o resultado da negociação e deixa o gestor simular parâmetros da política sobre os 60 mil casos em ~15 ms. A API do portal consome o modelo do engine (`models/*.json`) por um adapter (`MODEL_IMPL=app.modelo_enteros:ModeloEnteros`) e aplica a política operacional versionada no banco (`core/politica.py`); o mapa entre os parâmetros das duas políticas está em [`memory-bank/contratos.md`](memory-bank/contratos.md). Estado vivo do sistema, tabelas e fluxos: [`memory-bank/arquitetura.md`](memory-bank/arquitetura.md).

**Contratos** (`src/enteros/schemas.py`): `CaseFeatures` (UF, sub-assunto, valor da causa, status de cada subsídio
`presente|ausente|inconsistente`, e opcionais da IA: titularidade da conta, liveness, parcelas pagas, saldo, dano moral
pedido, contradições, red flags) → `Recomendacao` (decisão `defesa|acordo|instruir`, faixa, p_perda e intervalo,
condenação p20/p50/p80, EV de defesa e de acordo, escada, decomposição, VOI por documento, motivos, regras acionadas,
contribuições por feature, versões da política e do modelo).

**Custo e performance**: engine < 1 ms; API < 50 ms; IA documental estimada em 2–3 chamadas/caso com modelo barato e
cache por hash → **≈ R$ 0,05–0,15 por caso, < R$ 1 mil/mês** para 5 mil casos, contra R$ 5–9 milhões/mês de economia.

---

## 7. Divisão de trabalho e cronograma

| Trilha | Entrega | Pasta | Estado |
|---|---|---|---|
| A · Dados/Política | loader, modelos calibrados, engine EV, escada, VOI, `policy.yaml`, backtest, API, testes | `src/enteros/{data,policy,backtest,api}` | ✅ esta entrega |
| B · IA documental | extratores por documento, cruzador de fatos/contradições, contato do adverso, minutas, golden set + `make eval` | `src/enteros/ia/` | 🔧 |
| C · UX advogado | portal: login, casos, caso (recomendação, PDFs em nova aba com recibo de leitura, decisão com cronômetro, resultado; minutas e contato do adverso só quando a trilha B entregar), link mágico `/api/demo` | `src/web/src/pages/advogado`, `src/api` | ✅ básico · 🔧 polimento |
| D · Banco/Monitor | decisões em Postgres, aderência (desvio de tipo/valor, justificativas, por escritório/advogado/semana), efetividade (aceite real × hipótese, economia realizada), simulação de parâmetros nos 60k, aprovações | `src/api/app/services/{metricas,backtest}.py`, `src/web/src/pages/gestor` | ✅ números · 🔧 gráficos e experimento |
| E · Entrega | deck 15 min, vídeo 2 min, README/SETUP finais | `docs/` | 🔧 |

Cronograma (12→13/09): H0–2 scaffold + dados + engine · H2–8 trilhas em paralelo · H8–11 integrar os 2 casos ponta a
ponta · H11–13 números do backtest no deck · H13–14 vídeo · H14–15 buffer · **submissão até 04:00** (prazo 04:30).

---

## 8. Status por requisito

| # | Requisito | Onde | Estado |
|---|---|---|---|
| 1 | Regra de decisão acordo × defesa | `policy/engine.py` (EV + faixas + regras duras), `policy.yaml` | ✅ |
| 2 | Sugestão de valor | `policy/negotiation.py` (escada abertura/alvo/teto, decomposição) | ✅ |
| 3 | Acesso à recomendação | `enteros/api/main.py` (`POST /recomendacao`); portal `src/web` (`/casos/:id`, resumo copiável, link mágico `/api/demo` para a banca) | ✅ |
| 4 | Monitoramento de aderência | portal: decisão gravada contra a recomendação vista, justificativa obrigatória no desvio, aprovação de acordos fora da banda, `GET /api/dashboard/aderencia` | ✅ |
| 5 | Monitoramento de efetividade | `backtest/` (economia vs. baselines, sensibilidade, calibração); portal: resultado da negociação, aceite real × hipótese, economia realizada, `GET /api/dashboard/efetividade` | ✅ · 🔧 experimento de bandas |

---

## 9. Limitações conhecidas
- Base sintética e uniforme por UF; sem datas → sem modelo de duração nem de custo de capital observado.
- Só 280 acordos, todos aceitos → curva de aceite é premissa (por isso o experimento de bandas).
- Custos de defesa (honorários, custas, escritório) são parâmetros a confirmar com o jurídico; o backtest mostra a sensibilidade.
- IA lê PDFs digitais; autos escaneados exigem OCR. Dois processos exemplo → golden set precisa de casos sintéticos.
- Sem dados do advogado da parte autora (OAB) → detecção de litigância predatória é próximo passo.

## 10. Próximos passos com +1 mês
Integração ao EnterOS (webhook de novo caso → parecer); OCR; ingestão do resultado real de negociação e recalibração
mensal; bandit de oferta em produção com alçadas; features de litigância predatória (OAB, comarca, boilerplate);
modelo de duração com datas reais; expansão a cartão e outras modalidades.

---

## Como rodar
Ver [`SETUP.md`](SETUP.md). Resumo: `make install && make demo` roda o engine (sobre `data/exemplos/sinteticos.csv` se a
planilha da Enter não estiver em `data/raw/`); `make engine-api` → `http://localhost:8001/docs`. Portal completo com
Postgres: `make up && make jobs-docker` → `http://localhost:8080` (usuários e senha em `SETUP.md`).

## Enunciado original do desafio
O texto do organizador (contexto, requisitos, critérios, prazos e instruções de submissão) está em
[`docs/desafio.md`](docs/desafio.md).
