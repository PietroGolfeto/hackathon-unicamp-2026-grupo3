# Registro de premissas

Cada número usado pela política é **observado** na base de 60 mil sentenças (O), é uma **premissa declarada** que o
banco deve confirmar (H) ou é uma **escolha de política** (P). Parâmetros ficam em `src/enteros/policy/policy.yaml`
(versão `2026.09.12-v2`); os observados são recalculados por `make train` / `make backtest` / `make compare-models` e
gravados em `models/*.json`, `docs/backtest/resumo.json` e `docs/modelo/comparacao.json`.

## Observado na base

| # | Fato | Valor | Onde é usado |
|---|---|---|---|
| O1 | P(perda) logística aditiva em contrato, extrato, comprovante, demonstrativo, sub-assunto e UF (sem os 280 acordos) | AUC 0,9226 · log-loss 0,308 · Brier 0,093 · ECE 0,003 (out-of-fold, 5 folds); custo de decisão OOF R$ 242,7M no cenário `comparacao` | `policy/model.py::ModeloPerda`; `models/modelo_perda.json` |
| O2 | Dossiê e laudo não alteram a perda | Δ 0,0 p.p.; Wald p = 0,20 e 0,28; LR conjunto p = 0,26 | exportados com coeficiente 0; slide de subsídios |
| O3 | Valor da causa não altera a probabilidade de perder | corr 0,0006; 30–31% de perda em todos os decis | só multiplicador na função de perda |
| O4 | UF: 10 de 25 significativas; sd dos efeitos 0,32 × SE 0,10 | τ = 0,30; encolhimento médio 0,90 (AP +0,97, AM +0,89 reais; maioria ruído) | efeito parcialmente agrupado; UF desconhecida = UF média |
| O5 | Interações, saturação, valor da causa, gradient boosting, tabelas de células | tudo a ≤ 0,001 de AUC e < R$ 1M de custo OOF da logística | `docs/modelo/comparacao.md` |
| O6 | Severidade (condenação ÷ VC dado perda em sentença) por UF × sub-assunto | média 0,71; MA 0,60 → AM/AP 0,84; Genérico 0,65 × Golpe 0,72. Procedência ≈ U(0,80–1,00) flat por UF; parcial 0,48–0,82 por UF; P(procedência \| perda) 0,28 → 0,45 | `policy/ratio.py`; `models/ratio_condenacao.json` (média, p20/p50/p80, p_procedencia) |
| O7 | Extinção | 23% da base; ⅓ constante dos êxitos em todo estrato de docs (P(ext \| êxito) ≈ 0,33) | tratada como êxito; não é sinal de litigância |
| O8 | Acordos históricos | 280; razão pago/causa ≈ U(0,20–0,40), média 0,298, mediana 0,29; 74% sem contrato; só aceites (censura) | fora do treino; âncora de H1; custo real no backtest |
| O9 | Coocorrência dos documentos | P(contrato \| extrato) 0,79 × 0,42 sem extrato; dossiê/laudo independentes | `q_doc` = P(doc \| padrão dos outros 3 docs preditivos) em `models/modelo_perda.json` |
| O10 | Tabela de segmentos | 831 células sub × 4 docs × UF com p previsto e n observado | `models/segmentos.json` (saída do modelo, não estimador) |

## Premissas declaradas (confirmar com o banco / jurídico)

| # | Parâmetro | Valor | Faixa testada | Fonte | Onde é usado |
|---|---|---|---|---|---|
| H1 | Curva de aceite: 50% dos autores aceitam a 30% do VC; largura 0,06 | `oferta.aceite_s50`, `aceite_largura` | s50 0,25 → 35% · 0,40 → 24% · 0,50 → 18% de economia | ancorada em O8, que só tem aceites e é majoritariamente de casos sem contrato → conservadora para casos fortes | `policy/negotiation.py` |
| H2 | Escritório por processo defendido até sentença | R$ 1.200 | ×0,5 / ×1,5 (31,3% / 30,9%) | tabelas de honorários por ato em contencioso de massa | EV de defesa |
| H3 | Escritório por acordo (negociar + formalizar) | R$ 300 | — | idem | EV de acordo |
| H4 | Sucumbência sobre a condenação | 15% | 10% / 20% (29,5% / 32,3%) | CPC art. 85 §2 (10–20%); JEC só em recurso (Lei 9.099 art. 55) | EV de defesa |
| H5 | Custas/preparo quando perde | 2% do VC | 0% (30,3%) | reembolso + preparo; gratuidade de justiça frequente | EV de defesa |
| H6 | Correção + juros até o pagamento | 1% a.m. × 18 meses = 1,196 | 10 / 22 meses (28,4% / 32,2%) | IPCA + juros legais (SELIC − IPCA, Lei 14.905/2024); 12–24 meses em vara | EV de defesa |
| H7 | Custo de o back-office localizar um subsídio | R$ 80 + 5 dias de espera (correção sobre o EV) | — | premissa | EVSI |
| H8 | Cenário JEC | sem custas nem sucumbência em 1º grau; 9 meses | economia 22,9% | Lei 9.099 art. 55 | `cenarios.jec` na sensibilidade |
| H9 | Chance de localizar um subsídio ausente | q_d de O9 (limite superior) | × 0,5 / 0,75 / 1 → instruir em 24% / 31% / 34% dos casos | premissa | EVSI |
| H10 | Buscar e não achar piora p | probabilidade total: `p_falha = (p − q·p_com)/(1 − q)` (clip em [p, 1]); buscas independentes entre documentos; deslocamentos em log-odds somam | — | coerência bayesiana; a leitura "subsídio como intervenção" (ganho se encontrar) é limite superior reportado à parte | `policy/engine.py::analise_subsidios` |
| H11 | Saldo devedor baixado no acordo | informado pela IA documental, senão 0; entra nos dois ramos do EV e no teto | — | perder em juízo também anula o contrato | `policy/negotiation.py`, `engine.py` |
| H12 | Cenário fixo para comparar modelos | oferta 30% do VC, aceite 65% | — | mediana de O8; centro da sensibilidade | `comparacao` no yaml; `make compare-models` |

## Escolhas de política

| # | Escolha | Valor | Onde |
|---|---|---|---|
| P1 | Faixas de comunicação | verde < 15% · vermelha > 60% de perda; entre elas decide o menor custo esperado | `policy/engine.py` |
| P2 | Instruir | só adia um acordo; conjunto de maior EVSI se EVSI ≥ 2% do VC; defesas listam docs a pedir em paralelo | `faixas.evsi_min_pct_causa` |
| P3 | Escada | teto = 90% do EV de litigar − saldo (e ≤ 70% do VC); piso 10% do VC ou devolução simples; abertura = alvo − 20% | `oferta.*` |
| P4 | Sinais que forçam acordo | crédito em conta de terceiro; liveness ausente em canal digital (Súmula 479 STJ) | `regras_duras` |
| P5 | Decisão sensível | IC95 de p cruza p\* → revisar com o gestor (2,2% dos casos) | `engine.py` |
| P6 | Exploração para aprender H1 | 15% dos acordos com banda aleatória {25%, 30%, 35%} do VC | monitoramento (próxima fase) |

## Limitações conhecidas
- A base é sintética e uniforme por UF (2.308 processos cada); sem datas → sem modelo de duração nem corte temporal.
- Só 280 acordos, todos aceitos: a curva de aceite (H1) é premissa; por isso a sensibilidade a s50 e a exploração P6.
- Todos os 60 mil casos foram até a sentença: o lado acordo do backtest é hipótese; a banda (± 0,4 p.p.) mede só variação amostral.
- Custos de defesa (H2–H8) são parâmetros a confirmar com o jurídico do banco; o backtest traz a sensibilidade de cada um.
- q_d (H9) é limite superior; "ausente" na base mistura "não existe" e "existe, não foi localizado".
- Sem dados do advogado da parte autora (OAB) → litigância predatória fica como próximo passo.
