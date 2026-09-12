# Registro de premissas

Cada número usado pela política é **observado** na base de 60 mil sentenças ou é uma **premissa declarada** que o
banco deve confirmar. Parâmetros ficam em `src/enteros/policy/policy.yaml`; os observados são recalculados por
`make train` e gravados em `models/*.json`.

| # | Parâmetro | Valor | Fonte | Onde é usado |
|---|---|---|---|---|
| O1 | P(perda) por segmento (sub-assunto × contrato × extrato × comprovante × demonstrativo × UF) | tabela com 831 segmentos, shrinkage k=20 para o pai | **observado** | `policy/model.py::SegmentTable` |
| O2 | P(perda) logística (6 docs + sub-assunto + UF) | AUC 0,922 · Brier 0,093 · ECE 0,003 (out-of-fold) | **observado** | `policy/model.py::ModeloPerda` |
| O3 | Condenação ÷ valor da causa dado perda, por UF × sub-assunto | média 0,70 (0,60 MA → 0,84 AP); p20/p50/p80 | **observado** | `policy/ratio.py` |
| O4 | Acordos históricos | 280 casos a 20–40% do VC, mediana 0,29 | **observado** | âncora de H1 |
| O5 | Dossiê e laudo não alteram a perda | Δ 0,0 p.p. | **observado** | contribuições; slide de subsídios |
| H1 | Curva de aceite: 50% dos autores aceitam a 30% do VC; largura 0,06 | `oferta.aceite_s50`, `aceite_largura` | **premissa** (ancorada em O4; a base só tem acordos aceitos) | `policy/negotiation.py` |
| H2 | Custo do escritório por processo defendido até sentença | R$ 1.200 | **premissa** | EV de defesa |
| H3 | Custo operacional de negociar/formalizar acordo | R$ 300 | **premissa** | EV de acordo |
| H4 | Honorários de sucumbência sobre a condenação | 15% (CPC art. 85: 10–20%) | **premissa legal** | EV de defesa |
| H5 | Custas quando perde | 2% do valor da causa | **premissa** | EV de defesa |
| H6 | Correção + juros até o pagamento | 1% a.m. por 18 meses (fator 1,196) | **premissa** (a base não tem datas) | EV de defesa |
| H7 | Custo de o back-office localizar um subsídio | R$ 80 | **premissa** | faixa amarela |
| H8 | Limiares de faixa | verde < 15% · vermelha > 60% · VOI mínimo 10% do VC | **escolha de política** (ver curva de indiferença no backtest) | `policy/engine.py` |
| H9 | Teto = 90% do custo esperado de litigar; piso 10% do VC; teto 70% do VC; abertura = alvo − 20% | `oferta.*` | **escolha de política** | `policy/negotiation.py` |
| H10 | Sinais que forçam acordo | crédito em conta de terceiro; liveness ausente em canal digital | **escolha de política** (Súmula 479 STJ) | `policy/engine.py` |
| H11 | Exploração para aprender H1 | 15% dos acordos com banda aleatória {25%, 30%, 35%} do VC | **desenho experimental** | monitoramento (próxima fase) |

## Limitações conhecidas
- A base é sintética e uniforme por UF (2.308 processos cada); sem datas → sem modelo de duração.
- Só 280 acordos, todos aceitos: a curva de aceite (H1) é premissa; por isso o experimento H11.
- Custos de defesa (H2–H7) são parâmetros a confirmar com o jurídico do banco; o backtest traz sensibilidade.
- Sem dados do advogado da parte autora (OAB) → litigância predatória fica como próximo passo.
