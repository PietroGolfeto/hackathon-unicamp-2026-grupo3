# Dados

## Arquivos entregues pela organização (em `data/`, não versionados)
| Arquivo | Linhas | Colunas |
|---|---|---|
| `Hackaton_Enter_Base_Candidatos.xlsx - Resultados dos processos.csv` | 60.000 | Número do processo, UF, Assunto, Sub-assunto, Resultado macro, Resultado micro, Valor da causa, Valor da condenação/indenização |
| `Hackaton_Enter_Base_Candidatos.xlsx - Subsídios disponibilizados.csv` | 60.000 | Número do processo**s**, Contrato, Extrato, Comprovante de crédito, Dossiê, Demonstrativo de evolução da dívida, Laudo referenciado |
| `exemplos/<numero>/autos/*.pdf`, `exemplos/<numero>/subsidios/*.pdf` | 2 pastas | petição inicial e documentos do banco; pasta com o nome do número CNJ, ignorada pelo git; `python -m app.cli ingest` lê |

Nada disso é versionado (decisão 19). Sem os CSVs a API sobe e a simulação de política fica desabilitada com aviso.

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
| `Extinção` | 23% da base, todas Êxito | mantida no backtest (decisão 5) |
| `Acordo` no micro | 280 linhas, Não Êxito | acordos históricos; valor = pago |
| Sub-assunto | Golpe 69% (êxito 63,6%) · Genérico 31% (êxito 83%) | feature forte |
| UF | 26 UFs, exatamente 2.308 cada; êxito de 51,6% (AP) a 79,2% (MA) | base sintética (dizer nas limitações); UF tem sinal |
| Valor da causa | R$ 1k–31k, mediana R$ 15k | **sem** efeito no êxito (69–70% em todas as faixas) |
| Condenação quando perde | mediana R$ 10k; razão condenação/causa p25 0,55 · p50 0,74 · p75 0,86; nunca zero | stub: p20 = 0,55·causa, p50 = 0,74·causa, p80 = 0,86·causa |
| Contrato presente | êxito 87% vs 25% ausente | preditor dominante |
| Extrato presente | êxito 81% vs 18% ausente | segundo preditor |
| Comprovante de crédito | 80% vs 53% | terceiro |
| Dossiê, Laudo | sem efeito | não são "críticos" apesar do nome |
| Nº de subsídios | 0→0% · 1→3% · 2→13% · 3→34% · 4→64% · 5→87% · 6→96% | monotônico; stub por lookup funciona |
| Soma das condenações | R$ 193M em 60k = R$ 3.216 por processo | ordem de grandeza do slide financeiro |

## Backtest com scores stub (lookup in-sample) e params default
| Cenário | Acordo | Política | Defender tudo | Acordar tudo |
|---|---|---|---|---|
| defaults, com Extinção | 49,7% | R$ 313M | R$ 392M | R$ 283M |
| defaults, sem Extinção | 55,3% | R$ 270M | R$ 351M | R$ 246M |
Leitura: com custas R$ 1.500 + 10% de honorários, defender custa ≥ R$ 3k por processo, enquanto uma oferta no piso (10% da causa) com 65% de aceite custa menos; por isso "acordar tudo" vence a política sob essa hipótese. Calibração de P1 na H5: piso/fator de oferta e taxa de aceite realistas (meta 25–40% de acordo), ou custo de defesa menor. `load-historico` roda em 0,2 s; `simular` em ~15 ms.

## Processos exemplo (do vencedor anterior; confirmar que são os mesmos)
`0654321-09.2024.8.04.0001` (Manaus/AM): idoso, aposentado, contratação por app, crédito caiu em conta da Caixa que não é do autor, boletim de ocorrência, reclamação BACEN. `0801234-56.2024.8.10.0001` (MA): 6 subsídios presentes.
