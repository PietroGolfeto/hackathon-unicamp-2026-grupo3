# Benchmark da compressão de tokens do extractor

Parsing `2026-09-12.2` · prompt `2026-09-12.4` · tokens: tiktoken 0.14.0 / o200k_base · 5 repetições (mediana) · pdftotext version 26.07.0 · Python 3.12.13

## Resumo por processo

| Processo | Docs | Chars bruto → brief | Tokens bruto → brief | Redução | Entrada estimada | Cabeçalho+pistas | Tempo total (ms) | Leitura (ms) |
|---|---|---|---|---|---|---|---|---|
| 0801234-56.2024.8.10.0001 | 7 | 48.077 → 18.809 | 12.296 → 5.540 | 54.9% | 7.234 | 341 tok, 4 pistas | 551,6 | 120,5 |
| 0654321-09.2024.8.04.0001 | 4 | 37.982 → 13.460 | 10.039 → 3.750 | 62.6% | 5.444 | 254 tok, 5 pistas | 89,2 | 65,4 |
| 0001234-56.2024.8.13.0001 | 4 | 8.902 → 7.567 | 2.243 → 2.264 | -0.9% | 3.958 | 267 tok, 6 pistas | 6,1 | 0,2 |

Agregado: 24.578 → 11.554 tokens (53.0% a menos). Caracteres por token: 3.86 no texto bruto, 3.45 no brief (o parsing assume 4).

## Tokens que sobrevivem a cada etapa

| Processo | Bruto | Após segurança | Após parsing (blocos) | Brief (com cabeçalho) | + instruções e moldura |
|---|---|---|---|---|---|
| 0801234-56.2024.8.10.0001 | 12.296 | 12.283 | 5.192 | 5.540 | 7.234 |
| 0654321-09.2024.8.04.0001 | 10.039 | 10.031 | 3.493 | 3.750 | 5.444 |
| 0001234-56.2024.8.13.0001 | 2.243 | 2.241 | 1.994 | 2.264 | 3.958 |

A segurança quase não corta (só remove invisíveis, controle e linhas com instrução embutida); o parsing é a etapa que comprime. O brief acrescenta cabeçalho, pistas e um header por documento.

## Tempo por etapa (ms, mediana)

| Processo | Leitor | Leitura | Segurança | Parsing | Brief | Total | preparar() |
|---|---|---|---|---|---|---|---|
| 0801234-56.2024.8.10.0001 | pdftotext | 120,5 | 11,1 | 422,9 | 0,3 | 551,6 | 536,5 |
| 0801234-56.2024.8.10.0001 | pypdf | 40,5 | 7,8 | 16,1 | 0,1 | 64,4 | 69,6 |
| 0654321-09.2024.8.04.0001 | pdftotext | 65,4 | 8,4 | 15,2 | 0,2 | 89,2 | 90,7 |
| 0654321-09.2024.8.04.0001 | pypdf | 33,6 | 6,2 | 10,3 | 0,1 | 50,1 | 49,6 |
| 0001234-56.2024.8.13.0001 | pdftotext | 0,2 | 1,9 | 3,9 | 0,1 | 6,1 | 6,2 |

## Por documento

| Proc. | Arquivo | Tipo | Pág. | Tok bruto | Tok bloco | Redução | Trechos/limite | Cortou | Tok fatos |
|---|---|---|---|---|---|---|---|---|---|
| 0801234 | 01_Autos_Processo_0801234-56-2024-8-10-0001. | peticao | 8 | 4.024 | 2.058 | 49% | 6.749/7.000 (96%) | sim | 295 |
| 0801234 | 02_Contrato_502348719.pdf | contrato | 2 | 1.486 | 740 | 50% | 1.360/2.200 (62%) | não | 258 |
| 0801234 | 03_Extrato_Bancario.pdf | extrato | 1 | 410 | 579 | -41% | 722/2.500 (29%) | não | 219 |
| 0801234 | 04_Comprovante_de_Credito_BACEN.pdf | comprovante_credito | 2 | 853 | 443 | 48% | 590/1.600 (37%) | não | 212 |
| 0801234 | 05_Dossie_Veritas.pdf | dossie | 2 | 805 | 512 | 36% | 1.514/2.000 (76%) | não | 106 |
| 0801234 | 06_Demonstrativo_Evolucao_Divida.pdf | demonstrativo_divida | 3 | 3.808 | 332 | 91% | 461/1.200 (38%) | não | 123 |
| 0801234 | 07_Laudo_Referenciado.pdf | laudo_referenciado | 2 | 910 | 528 | 42% | 984/2.200 (45%) | não | 210 |
| 0654321 | 01_Autos_Processo_0654321-09-2024-8-04-0001. | peticao | 8 | 3.836 | 2.075 | 46% | 6.643/7.000 (95%) | não | 344 |
| 0654321 | 02_Comprovante_de_Credito_BACEN.pdf | comprovante_credito | 2 | 844 | 434 | 49% | 609/1.600 (38%) | não | 203 |
| 0654321 | 03_Demonstrativo_Evolucao_Divida.pdf | demonstrativo_divida | 3 | 4.385 | 331 | 92% | 457/1.200 (38%) | não | 123 |
| 0654321 | 04_Laudo_Referenciado.pdf | laudo_referenciado | 2 | 974 | 653 | 33% | 1.511/2.200 (69%) | sim | 221 |
| 0001234 | peticao_inicial.txt | peticao | - | 1.201 | 1.265 | -5% | 2.967/7.000 (42%) | não | 343 |
| 0001234 | comprovante_credito.txt | comprovante_credito | - | 375 | 268 | 29% | 207/1.600 (13%) | não | 160 |
| 0001234 | demonstrativo_evolucao_divida.txt | demonstrativo_divida | - | 425 | 249 | 41% | 376/1.200 (31%) | não | 86 |
| 0001234 | laudo_referenciado.txt | laudo_referenciado | - | 242 | 212 | 12% | 445/2.200 (20%) | não | 59 |

`Tok fatos` é a linha "Fatos detectados por regra" de cada bloco: repete valores que já estão nos trechos literais e é a parte do brief que mais cresce com o parsing.

## Orçamento e overhead fixo

| Componente | Tokens |
|---|---|
| instrucoes | 1.653 |
| moldura_da_entrada | 40 |
| esquema_json (indicativo) | 1.460 |

Limites de caracteres: brief 20.000, piso da petição 4.500; por tipo: peticao 7.000, contrato 2.200, extrato 2.500, comprovante_credito 1.600, dossie 2.000, demonstrativo_divida 1.200, laudo_referenciado 2.200, outro 1.200. O laço de encolhimento em `montar_brief` não rodou em nenhum processo medido.

## Baselines de mesmo orçamento (o que a seleção por regra ganha sobre cortar a cabeça do texto)

| Processo | Variante | Tokens | Fatos-chave preservados |
|---|---|---|---|
| 0801234-56.2024.8.10.0001 | bruto | 12.289 | 100% |
| 0801234-56.2024.8.10.0001 | brief | 5.540 | 100% |
| 0801234-56.2024.8.10.0001 | ingenuo_mesmo_orcamento | 5.254 | 70% |
| 0801234-56.2024.8.10.0001 | ingenuo_limites_por_tipo | 5.276 | 70% |
| 0654321-09.2024.8.04.0001 | bruto | 10.034 | 100% |
| 0654321-09.2024.8.04.0001 | brief | 3.750 | 100% |
| 0654321-09.2024.8.04.0001 | ingenuo_mesmo_orcamento | 3.658 | 68% |
| 0654321-09.2024.8.04.0001 | ingenuo_limites_por_tipo | 3.592 | 68% |
| 0001234-56.2024.8.13.0001 | bruto | 2.241 | 100% |
| 0001234-56.2024.8.13.0001 | brief | 2.264 | 100% |
| 0001234-56.2024.8.13.0001 | ingenuo_mesmo_orcamento | 1.918 | 100% |
| 0001234-56.2024.8.13.0001 | ingenuo_limites_por_tipo | 1.942 | 100% |

`ingenuo_mesmo_orcamento` corta cada documento na cabeça com os mesmos caracteres do bloco do brief; `ingenuo_limites_por_tipo` corta no limite de caracteres do tipo. Denominador: fatos-chave presentes no texto bruto.

## Fatos-chave que o brief perdeu

- 0801234-56.2024.8.10.0001: 23 fatos no bruto, 100% no brief. Nenhum perdido.
- 0654321-09.2024.8.04.0001: 22 fatos no bruto, 100% no brief. Nenhum perdido.
- 0001234-56.2024.8.13.0001: 17 fatos no bruto, 100% no brief. Nenhum perdido.

## Entidades distintas retidas no brief, por tipo de documento

| Tipo | valores R$ | datas | percentuais | identificadores 6+ dígitos |
|---|---|---|---|---|
| peticao | 11/13 | 9/13 | 0/1 | 11/21 |
| contrato | 5/5 | 5/5 | 3/3 | 1/1 |
| extrato | 0/0 | 7/7 | 0/0 | 2/2 |
| comprovante_credito | 6/6 | 9/9 | 4/4 | 5/8 |
| dossie | 0/0 | 0/0 | 2/2 | 1/1 |
| demonstrativo_divida | 9/9 | 6/163 | 3/3 | 3/3 |
| laudo_referenciado | 6/6 | 9/9 | 6/6 | 4/4 |

O demonstrativo perde a tabela de parcelas por desenho (vira contagem por regra); a petição perde datas e valores da fundamentação jurídica e dos anexos, que não entram no brief.

## Leitores de PDF: pdftotext × pypdf

| Processo | Leitor | Chars bruto | Tokens bruto | Tokens brief | Fatos no brief | Leitura (ms) | Brief igual? |
|---|---|---|---|---|---|---|---|
| 0801234-56.2024.8.10.0001 | pdftotext | 48.077 | 12.296 | 5.540 | 100% | 120,5 | sim |
| 0801234-56.2024.8.10.0001 | pypdf | 33.288 | 11.305 | 4.548 | 87% | 40,5 | não |
| 0654321-09.2024.8.04.0001 | pdftotext | 37.982 | 10.039 | 3.750 | 100% | 65,4 | sim |
| 0654321-09.2024.8.04.0001 | pypdf | 25.659 | 9.118 | 3.381 | 91% | 33,6 | não |

## Calibração com chamadas reais (cache em disco)

| Processo | Modelo | Prompt | Brief tok | Entrada estimada | Entrada real | Overhead | Saída real |
|---|---|---|---|---|---|---|---|
| 0801234-56.2024.8.10.0001 | gpt-4.1-mini-2025-04-14 | 2026-09-12.4 | 5.540 | 7.234 | 8.485 | 1.251 | 1.151 |
| 0654321-09.2024.8.04.0001 | gpt-5-mini-2025-08-07 | 2026-09-12.4 | 3.750 | 5.444 | 6.693 | 1.249 | 2.786 |
| 0801234-56.2024.8.10.0001 | gpt-4o-mini-2024-07-18 | 2026-09-12.3 (antigo) | 5.244 | 6.938 | 7.932 | 994 | 821 |
| 0801234-56.2024.8.10.0001 | gpt-4o-mini-2024-07-18 | 2026-09-12.2 (antigo) | 5.157 | 6.851 | 7.832 | 981 | 811 |
| 0654321-09.2024.8.04.0001 | gpt-5-mini-2025-08-07 | 2026-09-12.3 (antigo) | 3.750 | 5.444 | 6.436 | 992 | 3.046 |
| 0654321-09.2024.8.04.0001 | gpt-4o-mini-2024-07-18 | 2026-09-12.3 (antigo) | 3.750 | 5.444 | 6.438 | 994 | 901 |
| 0801234-56.2024.8.10.0001 | gpt-4.1-mini-2025-04-14 | 2026-09-12.3 (antigo) | 5.540 | 7.234 | 8.228 | 994 | 1.171 |
| 0654321-09.2024.8.04.0001 | gpt-4.1-mini-2025-04-14 | 2026-09-12.3 (antigo) | 3.750 | 5.444 | 6.438 | 994 | 1.557 |
| 0801234-56.2024.8.10.0001 | gpt-5-mini-2025-08-07 | 2026-09-12.3 (antigo) | 5.244 | 6.938 | 7.930 | 992 | 2.461 |
| 0654321-09.2024.8.04.0001 | gpt-4o-mini-2024-07-18 | 2026-09-12.1 (antigo) | 3.611 | 5.305 | 6.049 | 744 | 903 |
| 0801234-56.2024.8.10.0001 | gpt-4o-mini-2024-07-18 | 2026-09-12.1 (antigo) | 5.157 | 6.851 | 7.595 | 744 | 736 |
| 0801234-56.2024.8.10.0001 | gpt-5-mini-2025-08-07 | 2026-09-12.3 (antigo) | 5.540 | 7.234 | 8.226 | 992 | 2.756 |
| 0654321-09.2024.8.04.0001 | gpt-4o-mini-2024-07-18 | 2026-09-12.2 (antigo) | 3.611 | 5.305 | 6.286 | 981 | 789 |
| 0654321-09.2024.8.04.0001 | gpt-4.1-mini-2025-04-14 | 2026-09-12.4 | 3.750 | 5.444 | 6.695 | 1.251 | 1.218 |
| 0801234-56.2024.8.10.0001 | gpt-5-mini-2025-08-07 | 2026-09-12.4 | 5.540 | 7.234 | 8.483 | 1.249 | 2.724 |

Overhead da API sobre a estimativa (prompt atual): mediana 1250 tokens, faixa 1249–1251: é o esquema JSON da saída estruturada e a moldura de mensagens. Instruções antigas tokenizam diferente; as linhas marcadas como antigas não são comparáveis.

## Stress e escala (casos sintéticos a partir da pasta de testes)

| Caso | Docs | Chars bruto | Tok bruto | Tok brief | ≤ limite | Encolheu | Piso da petição | Valor da causa | Achados | Total ms | Parsing ms | Segurança ms |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| peticao_longa_x60 | 4 | 75.330 | 20.002 | 2.886 | sim | não | sim | sim | 0 | 42,8 | 24,8 | 17,6 |
| extrato_3000_movimentos | 5 | 330.778 | 132.265 | 3.843 | sim | não | sim | sim | 0 | 220,3 | 157,7 | 61,9 |
| 15_docs_outro | 16 | 89.808 | 25.501 | 3.152 | sim | não | sim | sim | 0 | 59,3 | 42,0 | 16,3 |
| injecao_x300 | 4 | 28.996 | 5.843 | 2.264 | sim | não | sim | sim | 300 | 11,0 | 3,9 | 6,6 |
| escala_peticao_x1 | 4 | 8.896 | 2.243 | 2.239 | sim | não | sim | sim | 0 | 6,3 | 3,9 | 2,0 |
| escala_peticao_x5 | 4 | 13.400 | 3.447 | 2.861 | sim | não | sim | sim | 0 | 8,6 | 5,2 | 3,0 |
| escala_peticao_x20 | 4 | 30.290 | 7.962 | 2.861 | sim | não | sim | sim | 0 | 17,4 | 10,1 | 6,9 |
| escala_peticao_x50 | 4 | 64.070 | 16.992 | 2.861 | sim | não | sim | sim | 0 | 34,7 | 19,7 | 14,6 |

`Encolheu`: o laço de `montar_brief` precisou cortar trechos para caber em 20.000 caracteres. `Piso da petição`: quando encolheu, a petição ficou com pelo menos 80% de 4.500 caracteres.

## Custo por processo (uma chamada, sem cache)

| Processo | Modelo | Com brief | Sem compressão | 5.000 processos/mês (com brief) |
|---|---|---|---|---|
| 0801234-56.2024.8.10.0001 | gpt-5-mini | $0.0074 | $0.0091 | $37 |
| 0801234-56.2024.8.10.0001 | gpt-5-nano | $0.0015 | $0.0018 | $7 |
| 0801234-56.2024.8.10.0001 | gpt-4o-mini | $0.0028 | $0.0038 | $14 |
| 0654321-09.2024.8.04.0001 | gpt-5-mini | $0.0070 | $0.0085 | $35 |
| 0654321-09.2024.8.04.0001 | gpt-5-nano | $0.0014 | $0.0017 | $7 |
| 0654321-09.2024.8.04.0001 | gpt-4o-mini | $0.0025 | $0.0034 | $12 |
| 0001234-56.2024.8.13.0001 | gpt-5-mini | $0.0066 | $0.0066 | $33 |
| 0001234-56.2024.8.13.0001 | gpt-5-nano | $0.0013 | $0.0013 | $7 |
| 0001234-56.2024.8.13.0001 | gpt-4o-mini | $0.0023 | $0.0023 | $11 |

Preços de tabela (USD/1M tokens, entrada/saída): {'gpt-5-mini': (0.25, 2.0), 'gpt-5-nano': (0.05, 0.4), 'gpt-4o-mini': (0.15, 0.6)}. Saída assumida em 2800 tokens (mediana observada do gpt-5-mini com reasoning low). No gpt-5-mini a saída custa 8× a entrada: com o brief, a saída já pesa mais que a entrada na conta.

## Integridade

| Processo | Leitor | Brief = preparar() | Determinista | SHA do brief |
|---|---|---|---|---|
| 0801234-56.2024.8.10.0001 | pdftotext | sim | sim | e8bad5f55c5c |
| 0801234-56.2024.8.10.0001 | pypdf | sim | sim | 4bbc15f08949 |
| 0654321-09.2024.8.04.0001 | pdftotext | sim | sim | 1587de532eb4 |
| 0654321-09.2024.8.04.0001 | pypdf | sim | sim | 84ad91e3714a |
| 0001234-56.2024.8.13.0001 | pdftotext | sim | sim | 12a4b528740f |
