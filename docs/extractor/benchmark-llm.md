# Benchmark do extractor: pipeline e LLM

Duas medições sobre os dois processos exemplo da Enter (PDFs em `docs/Caso_01_…` e `docs/Caso_02_…`, não versionados):

1. **Pipeline sem LLM** (`make bench-extractor` → `docs/extractor/benchmark.md`): quanto texto chega ao modelo, quanto tempo leva e o que se perde.
2. **Chamadas reais ao LLM** (este arquivo): 4 modelos × 2 processos × 3 chamadas, saída conferida contra um gabarito objetivo por caso e contra os sinais esperados após as regras.

## Tabelas para o deck

### Pipeline determinístico (antes do LLM)

| Etapa | Caso 01 (7 PDFs, todos os subsídios) | Caso 02 (4 PDFs, sem contrato, extrato e dossiê) |
|---|---|---|
| Texto bruto dos PDFs | 48,1k caracteres · 12,3k tokens | 38,0k caracteres · 10,0k tokens |
| Brief enviado ao LLM | 18,8k caracteres · 5,5k tokens (**−55%**) | 13,5k caracteres · 3,8k tokens (**−63%**) |
| Fatos-chave literais preservados no brief | 23/23 (100%) | 22/22 (100%) |
| Corte ingênuo (cabeça de cada documento, mesmo orçamento) | 70% dos fatos | 68% dos fatos |
| Tempo PDF → brief (leitura, segurança, parsing) | 0,53 s | 0,09 s |
| Segunda leitura do mesmo processo (cache hit) | ~0,58 s, 0 tokens, 0 chamadas | ~0,12 s, 0 tokens, 0 chamadas |
| Custo fixo por chamada (instruções + esquema + moldura) | ~2,9k tokens | ~2,9k tokens |

Stress (casos sintéticos): extrato com 3.000 movimentos (330k caracteres) vira 3,8k tokens em 0,2 s; 300 instruções embutidas ("ignore as regras…") saem do brief e viram sinal DOCUMENTO_SUSPEITO em 11 ms; 16 documentos ou petição 60× maior ficam dentro do limite de 20k caracteres sem acionar o laço de encolhimento.

### Modelos (chamadas reais, prompt `2026-09-12.4`, medianas de 6 chamadas por modelo)

| Modelo | Gabarito (saída crua) | Sinais finais certos | Latência p50 (min–máx) | Tokens entrada → saída | Custo/processo (sem prompt cache) | 5.000 processos/mês |
|---|---|---|---|---|---|---|
| gpt-4o-mini | 90% | 6/6 | 7,7 s (6–12) | 7,6k → 0,95k | US$ 0.0017 | US$ 9 (≈ R$ 46) |
| gpt-4.1-mini | 97% | 6/6 | 9,5 s (7–12) | 7,6k → 1,21k | US$ 0.0050 | US$ 25 (≈ R$ 134) |
| gpt-5-nano | 87% | 4/6 | 16,8 s (10–18) | 7,6k → 2,65k | US$ 0.0014 | US$ 7 (≈ R$ 39) |
| gpt-5-mini (padrão) | 99% | 6/6 | 40,9 s (29–50) | 7,6k → 2,80k | US$ 0.0075 | US$ 38 (≈ R$ 203) |

`Gabarito`: 20 critérios no caso 01 e 21 no caso 02 (números do contrato, parcelas, saldo, canal, assinatura, liveness, banco depositário, idade, valores da causa e do dano moral, OAB, sinais que devem e não devem aparecer, contradição-chave, citar só documentos entregues), conferidos na saída crua do LLM, antes das regras. `Sinais finais certos`: chamadas em que, após a reconciliação por regra (decisão 42), o conjunto de sinais tem todos os obrigatórios e nenhum proibido.

Leitura: os sinais que a regra consegue decidir (idoso, BO, BACEN, sem contrato, crédito em conta de terceiro) saem certos com qualquer modelo, porque a regra entra se o LLM esqueceu e sai se ele inventou. A diferença entre modelos fica no que só o LLM preenche (tipo de assinatura, liveness, números do contrato, contradições) e na estabilidade entre chamadas. gpt-5-nano é o mais barato e o menos estável (uma chamada com 12/21 no caso 02); gpt-4.1-mini entrega os mesmos sinais finais que o gpt-5-mini em 1/4 do tempo e 1/3 a menos de custo; gpt-5-mini é o único que acertou o gabarito inteiro em 5 das 6 chamadas. Preços de tabela da OpenAI lidos em 2026-09-12; câmbio assumido R$ 5,40. Nas repetições dos gpt-5* a OpenAI serviu 6,5–8,3k tokens de entrada do prompt cache (mesmo prefixo em minutos); em produção cada processo é diferente e só as instruções (~1,7k tokens) se repetem, por isso a tabela usa o custo sem cache.

### Lacuna encontrada pelo benchmark

A regex `liveness_nao_localizado` não casa no laudo do caso 02: `pdftotext -layout` quebra a linha entre "não foi localizado nos arquivos digitais o" e "vídeo de liveness", e o padrão usa `[^.\n]{0,80}`, que não atravessa a quebra. Consequência: o sinal LIVENESS_AUSENTE_CANAL_DIGITAL depende de o LLM devolver `liveness = nao_localizado`; quando ele não devolve, a regra de canal digital apaga até o sinal que o LLM acertou (aconteceu em 2 das 3 chamadas do gpt-5-nano). Correção candidata: permitir quebra de linha no padrão (`[^.]{0,120}`) e cobrir com um teste com o texto do laudo.

---

# Detalhes da rodada com LLM

Prompt `2026-09-12.4` · 3 chamadas por modelo × processo (`forcar=True`, cache separado) · reasoning `low` nos gpt-5* · saída estruturada (`responses.parse`) · preços de tabela OpenAI de 2026-09-12, entrada em cache a 1/10 · medianas.

## Resumo por modelo (os dois processos juntos)

| Modelo | Chamadas | Tokens entrada | Tokens saída (raciocínio) | Latência p50 (min–máx) | Gabarito (saída crua) | Sinais finais certos | Custo/processo | 5.000 processos/mês |
|---|---|---|---|---|---|---|---|---|
| gpt-4o-mini | 6 | 7.590 | 952 | 7,7 s (6,2–11,9) | 90% | 6/6 | US$ 0.0017 | US$ 9 (≈ R$ 47) |
| gpt-4.1-mini | 6 | 7.590 | 1.210 | 9,5 s (7,3–12,1) | 97% | 6/6 | US$ 0.0048 | US$ 24 (≈ R$ 131) |
| gpt-5-nano | 6 | 7.588 | 2.650 (1.600) | 16,8 s (10,5–18,3) | 87% | 4/6 | US$ 0.0013 | US$ 6 (≈ R$ 34) |
| gpt-5-mini | 6 | 7.588 | 2.804 (1.216) | 40,9 s (29,3–49,6) | 99% | 6/6 | US$ 0.0058 | US$ 29 (≈ R$ 158) |

`Gabarito`: critérios objetivos por caso (números do contrato, parcelas, saldo, canal, assinatura, liveness, banco depositário, idade, valores da causa e do dano moral, OAB, sinais que devem e não devem aparecer, contradição-chave, citar só documentos entregues) conferidos na saída crua do LLM, antes das regras. `Sinais finais certos`: após a reconciliação por regra (decisão 42), o conjunto de sinais tem todos os obrigatórios e nenhum proibido.

## Por processo

| Modelo | Processo | Entrada | Saída (racioc.) | Latência p50 (min–máx) | Gabarito | Sinais finais | Contradições | Custo | Cache hit |
|---|---|---|---|---|---|---|---|---|---|
| gpt-4o-mini | Caso 01 (7 PDFs, todos os subsídios) | 8.485 | 898 | 11,6 s (6,2–11,9) | 18/20 (90%) | 3/3 | 1 | US$ 0.0018 | 579 ms, 0 tokens |
| gpt-4o-mini | Caso 02 (4 PDFs, sem contrato/extrato/dossiê) | 6.695 | 1.045 | 7,3 s (7,2–8,0) | 19/21 (90%) | 3/3 | 3 | US$ 0.0016 | 113 ms, 0 tokens |
| gpt-4.1-mini | Caso 01 (7 PDFs, todos os subsídios) | 8.485 | 1.038 | 8,9 s (7,3–11,0) | 20/20 (100%) | 3/3 | 1 | US$ 0.0051 | 588 ms, 0 tokens |
| gpt-4.1-mini | Caso 02 (4 PDFs, sem contrato/extrato/dossiê) | 6.695 | 1.283 | 9,6 s (9,5–12,1) | 19–20/21 (94%) | 3/3 | 3 | US$ 0.0047 | 113 ms, 0 tokens |
| gpt-5-nano | Caso 01 (7 PDFs, todos os subsídios) | 8.483 | 2.640 (1.600) | 16,6 s (12,7–18,3) | 19–20/20 (97%) | 3/3 | 3 | US$ 0.0011 | 563 ms, 0 tokens |
| gpt-5-nano | Caso 02 (4 PDFs, sem contrato/extrato/dossiê) | 6.693 | 3.199 (1.792) | 17,0 s (10,5–17,6) | 12–20/21 (78%) | 1/3 | 2 | US$ 0.0014 | 129 ms, 0 tokens |
| gpt-5-mini | Caso 01 (7 PDFs, todos os subsídios) | 8.483 | 2.757 (1.216) | 29,9 s (29,3–39,7) | 19–20/20 (98%) | 3/3 | 2 | US$ 0.0058 | 576 ms, 0 tokens |
| gpt-5-mini | Caso 02 (4 PDFs, sem contrato/extrato/dossiê) | 6.693 | 2.850 (1.216) | 45,1 s (42,1–49,6) | 21/21 (100%) | 3/3 | 3 | US$ 0.0059 | 120 ms, 0 tokens |

## O que cada modelo errou na saída crua (união das repetições)

- **gpt-4o-mini** · Caso 01 (7 PDFs, todos os subsídios): não inventou CREDITO_CONTA_TERCEIRO; não inventou LIVENESS_AUSENTE/SEM_CONTRATO. Sinais emitidos pelo LLM: CREDITO_CONTA_TERCEIRO, IDOSO, SEM_CONTRATO.
- **gpt-4o-mini** · Caso 02 (4 PDFs, sem contrato/extrato/dossiê): assinatura biometria; sinal LIVENESS_AUSENTE_CANAL_DIGITAL. Sinais emitidos pelo LLM: BOLETIM_OCORRENCIA, CREDITO_CONTA_TERCEIRO, IDOSO, RECLAMACAO_BACEN, SEM_CONTRATO.
- **gpt-4.1-mini** · Caso 01 (7 PDFs, todos os subsídios): nada. Sinais emitidos pelo LLM: IDOSO.
- **gpt-4.1-mini** · Caso 02 (4 PDFs, sem contrato/extrato/dossiê): assinatura biometria; sinal LIVENESS_AUSENTE_CANAL_DIGITAL. Sinais emitidos pelo LLM: BOLETIM_OCORRENCIA, CREDITO_CONTA_TERCEIRO, IDOSO, LIVENESS_AUSENTE_CANAL_DIGITAL, RECLAMACAO_BACEN, SEM_CONTRATO.
- **gpt-5-nano** · Caso 01 (7 PDFs, todos os subsídios): valor R$ 5.000. Sinais emitidos pelo LLM: IDOSO.
- **gpt-5-nano** · Caso 02 (4 PDFs, sem contrato/extrato/dossiê): 8 parcelas pagas; 84 parcelas; assinatura biometria; contradição-chave: nega a conta × crédito na Caixa; contrato nº 603827451; liveness não localizado; parcela R$ 180; saldo R$ 2.748,38; sinal IDOSO; sinal SEM_CONTRATO; valor R$ 8.500. Sinais emitidos pelo LLM: BOLETIM_OCORRENCIA, CANAL_DIGITAL_SEM_PERFIL, CREDITO_CONTA_TERCEIRO, IDOSO, LIVENESS_AUSENTE_CANAL_DIGITAL, OUTRO, RECLAMACAO_BACEN, SEM_CONTRATO.
- **gpt-5-mini** · Caso 01 (7 PDFs, todos os subsídios): não inventou CREDITO_CONTA_TERCEIRO. Sinais emitidos pelo LLM: CREDITO_CONTA_TERCEIRO, IDOSO.
- **gpt-5-mini** · Caso 02 (4 PDFs, sem contrato/extrato/dossiê): nada. Sinais emitidos pelo LLM: BOLETIM_OCORRENCIA, CANAL_DIGITAL_SEM_PERFIL, CREDITO_CONTA_TERCEIRO, IDOSO, LIVENESS_AUSENTE_CANAL_DIGITAL, RECLAMACAO_BACEN, SEM_CONTRATO.

## Todas as chamadas

| Modelo | Processo | Rep | Entrada | Cache | Saída | Racioc. | Segundos | Gabarito | Finais ok | Faltam | Sobram | Confiança |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| gpt-4o-mini | 0654321 | 1 | 6695 | 0 | 1071 | 0 | 7.99 | 19/21 | sim | — | — | 0.7 |
| gpt-4o-mini | 0654321 | 2 | 6695 | 0 | 982 | 0 | 7.22 | 19/21 | sim | — | — | 0.5 |
| gpt-4o-mini | 0654321 | 3 | 6695 | 0 | 1045 | 0 | 7.31 | 19/21 | sim | — | — | 0.5 |
| gpt-4o-mini | 0801234 | 1 | 8485 | 0 | 898 | 0 | 11.94 | 18/20 | sim | — | — | 0.8 |
| gpt-4o-mini | 0801234 | 2 | 8485 | 0 | 888 | 0 | 6.25 | 18/20 | sim | — | — | 0.7 |
| gpt-4o-mini | 0801234 | 3 | 8485 | 0 | 923 | 0 | 11.6 | 18/20 | sim | — | — | 0.9 |
| gpt-4.1-mini | 0654321 | 1 | 6695 | 0 | 1278 | 0 | 9.59 | 20/21 | sim | — | — | 0.8 |
| gpt-4.1-mini | 0654321 | 2 | 6695 | 0 | 1283 | 0 | 9.46 | 19/21 | sim | — | — | 0.7 |
| gpt-4.1-mini | 0654321 | 3 | 6695 | 0 | 1323 | 0 | 12.07 | 20/21 | sim | — | — | 0.8 |
| gpt-4.1-mini | 0801234 | 1 | 8485 | 0 | 1038 | 0 | 10.98 | 20/20 | sim | — | — | 0.9 |
| gpt-4.1-mini | 0801234 | 2 | 8485 | 0 | 942 | 0 | 7.26 | 20/20 | sim | — | — | 1.0 |
| gpt-4.1-mini | 0801234 | 3 | 8485 | 0 | 1141 | 0 | 8.94 | 20/20 | sim | — | — | 1.0 |
| gpt-5-nano | 0654321 | 1 | 6693 | 0 | 3199 | 1792 | 17.0 | 20/21 | sim | — | — | 0.65 |
| gpt-5-nano | 0654321 | 2 | 6693 | 6528 | 1835 | 640 | 10.46 | 12/21 | não | LIVENESS_AUSENTE_CANAL_DIGITAL | — | 0.58 |
| gpt-5-nano | 0654321 | 3 | 6693 | 6528 | 3380 | 2176 | 17.62 | 17/21 | não | LIVENESS_AUSENTE_CANAL_DIGITAL | — | 0.72 |
| gpt-5-nano | 0801234 | 1 | 8483 | 0 | 2640 | 1600 | 16.62 | 20/20 | sim | — | — | 1.0 |
| gpt-5-nano | 0801234 | 2 | 8483 | 8320 | 2274 | 960 | 12.66 | 19/20 | sim | — | — | 1.0 |
| gpt-5-nano | 0801234 | 3 | 8483 | 8320 | 2661 | 1600 | 18.34 | 19/20 | sim | — | — | 1.0 |
| gpt-5-mini | 0654321 | 1 | 6693 | 6528 | 3154 | 1280 | 49.63 | 21/21 | sim | — | — | 0.4 |
| gpt-5-mini | 0654321 | 2 | 6693 | 6528 | 2746 | 1088 | 45.09 | 21/21 | sim | — | — | 0.6 |
| gpt-5-mini | 0654321 | 3 | 6693 | 6528 | 2850 | 1216 | 42.09 | 21/21 | sim | — | — | 0.4 |
| gpt-5-mini | 0801234 | 1 | 8483 | 8320 | 2757 | 1216 | 29.31 | 19/20 | sim | — | — | 0.9 |
| gpt-5-mini | 0801234 | 2 | 8483 | 8320 | 2423 | 1152 | 29.85 | 20/20 | sim | — | — | 1.0 |
| gpt-5-mini | 0801234 | 3 | 8483 | 8320 | 2881 | 1472 | 39.7 | 20/20 | sim | — | — | 0.9 |
