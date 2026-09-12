# Dados

## Arquivos entregues pela organização (em `data/`, não versionados)
| Arquivo | Linhas | Colunas |
|---|---|---|
| `Hackaton_Enter_Base_Candidatos.xlsx - Resultados dos processos.csv` | 60.000 | Número do processo, UF, Assunto, Sub-assunto, Resultado macro, Resultado micro, Valor da causa, Valor da condenação/indenização |
| `Hackaton_Enter_Base_Candidatos.xlsx - Subsídios disponibilizados.csv` | 60.000 | Número do processo**s**, Contrato, Extrato, Comprovante de crédito, Dossiê, Demonstrativo de evolução da dívida, Laudo referenciado |
| `exemplos/<numero>/autos/*.pdf`, `exemplos/<numero>/subsidios/*.pdf` | 2 pastas | petição inicial e documentos do banco; pasta com o nome do número CNJ, ignorada pelo git; `python -m app.cli ingest` lê |

Nada disso é versionado (decisão 19). Sem os CSVs a API sobe e a simulação de política fica desabilitada com aviso. O engine (`src/enteros`) lê a **planilha** `data/raw/Hackaton_Enter_Base_Candidatos.xlsx` (mesmos dados, duas abas) e, sem ela, `data/exemplos/sinteticos.csv`.

## Regras de parsing
- CSV de subsídios tem **uma linha de legenda antes do cabeçalho**: ler com `header=1`.
- Coluna de junção é `Número do processo` num arquivo e `Número do processos` no outro. `core/colunas.py` normaliza ambos para `numero`.
- Valores monetários em BRL: `"13.534,00"`. Usar `core.colunas.parse_brl`.
- `Resultado macro`: `Êxito` → 1, `Não Êxito` → 0.
- Match entre os dois arquivos: 100%. Sem duplicatas de número.
- UF é derivável do número CNJ (segmento TR): `core/cnj.py`. Bate com a coluna UF em toda a base.

## Fatos da base
| Fato | Número | Implicação |
|---|---|---|
| Êxito global | 69,6% | base rate do stub; "defender tudo" já vence 7 em 10 |
| `Extinção` | 23% da base, todas Êxito; é ⅓ constante dos êxitos em todo estrato de docs (P(ext \| êxito) ≈ 0,33) | mantida no backtest (decisão 5); **não** é sinal de litigância predatória nem independe dos docs |
| `Acordo` no micro | 280 linhas, Não Êxito; razão pago/causa ≈ U(0,20–0,40), média 0,298; 74% sem contrato | não são sentenças: fora do treino de frequência e de severidade do engine; só âncora da curva de aceite |
| Sub-assunto | Golpe 69% (êxito 63,6%) · Genérico 31% (êxito 83%) | feature forte |
| UF | 26 UFs, exatamente 2.308 cada; êxito de 51,6% (AP) a 79,2% (MA) | base sintética (dizer nas limitações); UF tem sinal |
| Valor da causa | R$ 1k–31k, mediana R$ 15k | **sem** efeito no êxito (69–70% em todas as faixas) |
| Condenação quando perde | mediana R$ 10k; razão condenação/causa p25 0,55 · p50 0,74 · p75 0,86; nunca zero | stub: p20 = 0,55·causa, p50 = 0,74·causa, p80 = 0,86·causa |
| Severidade por UF (razão condenação/causa dado perda) | MA 0,60 · MS/MT 0,61 · maioria ≈ 0,68 · BA 0,80 · AM/AP 0,84; Genérico 0,65 × Golpe 0,715; Procedência ≈ U(0,80–1,00) flat por UF, Parcial varia 0,48–0,82 por UF; P(procedência \| perda) 0,28 (MA) → 0,39 (AP) | severidade **não** é constante: fica por UF × sub-assunto |
| Interações / valor da causa / árvores | logística aditiva 4 docs + sub + UF: AUC 0,9226 OOF; interações, saturação, VC e gradient boosting não mudam nada (≤ 0,001) | processo gerador aditivo em log-odds; escolha de modelo vale < R$ 1M de custo de decisão |
| Contrato presente | êxito 87% vs 25% ausente | preditor dominante |
| Extrato presente | êxito 81% vs 18% ausente | segundo preditor |
| Comprovante de crédito | 80% vs 53% | terceiro |
| Dossiê, Laudo | sem efeito | não são "críticos" apesar do nome |
| Nº de subsídios | 0→0% · 1→3% · 2→13% · 3→34% · 4→64% · 5→87% · 6→96% | monotônico; stub por lookup funciona |
| Soma das condenações | R$ 193M em 60k = R$ 3.216 por processo | ordem de grandeza do slide financeiro |

## Backtest da API (`POST /politicas/simular`) com params default
| Cenário | Acordo | Política | Defender tudo | Acordar tudo |
|---|---|---|---|---|
| scores do engine (adapter), com Extinção | 42,9% | R$ 318M | R$ 392M | R$ 281M |
| scores stub (lookup), com Extinção | 49,7% | R$ 313M | R$ 392M | R$ 283M |
| scores stub, sem Extinção | 55,3% | R$ 270M | R$ 351M | R$ 246M |
Leitura: com custas R$ 1.500 + 10% de honorários, defender custa ≥ R$ 3k por processo, enquanto uma oferta no piso (10% da causa) com 65% de aceite custa menos; por isso "acordar tudo" vence a política sob essa hipótese. Calibração de P1 na H5: piso/fator de oferta e taxa de aceite realistas (meta 25–40% de acordo), ou custo de defesa menor. `load-historico` roda em 0,2 s; `simular` em ~15 ms.

## Backtest do engine (P1, `make backtest`, premissas em `docs/premissas.md`)
| Medida | Valor |
|---|---|
| Modelo de perda (logística, OOF 5 folds, sem os 280 acordos) | AUC 0,923 · log-loss 0,308 · Brier 0,093 · ECE 0,003 · taxa de perda 30,1% |
| Defender tudo (condenação + honorários 15% + custas 2% + correção 1% a.m. × 18 meses + escritório R$ 1.200) | R$ 342,9M |
| Acordar tudo a 30% do VC, aceite 65% | R$ 313,3M (−8,6%) |
| Heurística "sem contrato → acordo" | R$ 260,7M (−24,0%) |
| Limiar fixo p_perda > 0,60 (3 grupos da UFMG) | R$ 257,9M (−24,8%; captura 56% do ganho máximo) |
| Política do engine (p OOF, escada + curva de aceite; acordo em 36% dos casos) | **R$ 236,8M, economia R$ 106M (31,0%; captura 70% do ganho máximo)** |
| Oráculo (resultado conhecido, mesma escada) | R$ 191,1M (−44,3%) — teto teórico |
| Banda do headline | 31,1% ± 0,4 p.p. entre folds; bootstrap IC95 30,6–31,4% |
| Sensibilidade ao aceite | 50% → 17% · 65% → 23% · 80% → 29% · curva → 31% |
| Sensibilidade à âncora s50 | 0,25 → 34,8% · 0,30 → 31,0% · 0,40 → 23,9% · 0,50 → 17,6% |
| Sensibilidade a custos | escritório ×0,5/×1,5, sucumbência 10/20%, tempo 10/22 meses: 28–32%; **JEC** (sem custas/sucumbência, 9 meses): 22,9% |
| Breakeven p\* (no alvo da escada) | médio 0,47 (p5 0,24 · p95 0,84); com oferta fixa de 30% do VC e aceite 65% ≈ 0,26; 2,2% dos casos sensíveis (IC cruza p\*) |
| Instruir (pedir contrato/extrato antes de acordar) | 33,6% dos casos (93% dos acordos) sob q_d cheio; 23,9% com q_d × 0,5; EVSI total R$ 50M (hipótese) |
| Por UF | economia de 21,7% (MA) a 42,9% (AP); % acordo 26% (MA) → 60% (AP) |
Os dois backtests (engine e API) usam resultados reais, mas premissas de custo diferentes; por isso os totais não batem. Ver decisão 25.

## Processos exemplo (do vencedor anterior; confirmar que são os mesmos)
`0654321-09.2024.8.04.0001` (Manaus/AM): idoso, aposentado, contratação por app, crédito caiu em conta da Caixa que não é do autor, boletim de ocorrência, reclamação BACEN. `0801234-56.2024.8.10.0001` (MA): 6 subsídios presentes.
