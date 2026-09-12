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
| Modelo de perda (logística, OOF 5 folds) | AUC 0,923 · Brier 0,093 · ECE 0,003 · taxa de perda 30,4% |
| Defender tudo (condenação + honorários 15% + custas 2% + correção 1% a.m. × 18 meses + escritório R$ 1.200) | R$ 342,9M |
| Acordar tudo no alvo (curva de aceite) | R$ 246,6M |
| Política do engine (acordo em 36% dos casos) | R$ 236,7M, economia R$ 106M (31%) |
| Faixas | verde 57% dos casos / 20% do custo · amarela 19% · vermelha 24% dos casos / 59% do custo |
Os dois backtests (engine e API) usam resultados reais, mas premissas de custo diferentes; por isso os totais não batem. Ver decisão 25.

## Processos exemplo (PDFs em `docs/Caso_01_…/` e `docs/Caso_02_…/`, não versionados; `make exemplos-docs` copia para `data/exemplos/`)
| Fato | Caso 01 `0801234-56.2024.8.10.0001` (São Luís/MA) | Caso 02 `0654321-09.2024.8.04.0001` (Manaus/AM) |
|---|---|---|
| Arquivos | 7 PDFs (autos + 6 subsídios), 1–8 páginas, com camada de texto, gerados por pypdf, sem scripts | 4 PDFs (autos + comprovante, demonstrativo, laudo); sem contrato, extrato e dossiê |
| Texto bruto → brief | 47,6k → 17,8k caracteres | 37,7k → 13,0k caracteres |
| Autor | Maria, 65 anos na data da petição (RG anexo), aposentada; pede R$ 15k de dano moral; causa R$ 20k | José, 61 anos, aposentado; BO nº 2024.005432 e RDR (BACEN) nº 12345678-9; dano moral R$ 18k; causa R$ 25k |
| Contrato | nº 502348719, R$ 5.000 em 72 × R$ 120, correspondente por telemarketing, assinatura manuscrita (dossiê: 91%), liveness 97,3% | nº 603827451, R$ 8.500 em 84 × R$ 180, app mobile com biometria; laudo admite que o vídeo de liveness não foi localizado |
| Crédito | conta própria no Banco UFMG; extrato mostra TED p/ conta própria no Bradesco, PIX a familiar e saque em São Luís — a petição diz que "jamais utilizou os valores" | conta na Caixa (ag 3245, cc 00012345-6) que o autor diz não ter |
| Parcelas | 21 de 72 pagas, saldo R$ 1.037,66 | 8 de 84 pagas, saldo R$ 2.748,38 |
Rodada real do extractor (prompt 2026-09-12.3, `make extrair`):
| Modelo | Caso 01 tokens in+out | Caso 02 tokens in+out | Qualidade |
|---|---|---|---|
| gpt-4o-mini | 7.932 + 821 | 6.438 + 901 | sinais certos só com a reconciliação por regra; contradições genéricas; citou "[Dossiê]" inexistente no caso 02; variou entre rodadas |
| gpt-5-mini (padrão) | 8.226 + 2.756 | 6.436 + 3.046 | sinais, fontes por arquivo e contradições certos (caso 02: conta na Caixa que o autor nega; caso 01: petição nega movimentação e o extrato mostra TED, PIX e saque após o crédito); acrescentou CANAL_DIGITAL_SEM_PERFIL no caso 02 |
Benchmark da compressão (`make bench-extractor`, tiktoken o200k_base, relatório em `docs/extractor/benchmark.md`): brief 12.296 → 5.540 tokens (caso 01, −55%) e 10.039 → 3.750 (caso 02, −63%); a entrada real da API é brief + 1.396 de instruções + ~1.250 de esquema e moldura (mediana do cache), ~2.650 tokens fixos por chamada. Fatos-chave literais (23, 22 e 17 por caso): 100% no brief; corte ingênuo da cabeça de cada documento com o mesmo orçamento preserva 68–70%. Custo no gpt-5-mini: US$ 0,0073 por processo com brief vs 0,0090 sem compressão; a saída (~2,8k tokens com reasoning low, US$ 2/M) é 77% da conta. Segunda rodada = cache hit, zero chamadas.
Achados do benchmark: (a) `RE_MOVIMENTO` gasta ~350 ms numa linha de extrato sem a coluna de saldo (`SALDO ANTERIOR` + espaços de layout): parsing do caso 01 leva 416 ms vs 15 ms no caso 02; grupos de tokens separados por um espaço (`(?:\S+[ \t])*?\S+`) capturam o mesmo em <1 ms. (b) Sem `pdftotext` (pypdf) o laudo vira um parágrafo único cortado em 600 chars: o brief perde "liveness não localizado" (caso 02) e os índices 91%/97,3% do dossiê (caso 01), ficando com 87–91% dos fatos. (c) A linha "Fatos detectados por regra" custa ~1,4k tokens por processo (26% do brief) e repete os trechos; o bloco do extrato sai 41% maior que o original. (d) Documentos pequenos (caso sintético dos testes) saem maiores que o original: cabeçalhos, fatos e pistas pesam ~500 tokens. (e) Nem 330k chars de extrato nem 16 documentos acionaram o laço de encolhimento de `montar_brief`: os limites por tipo bastam; tempo linear, ~0,5 ms por 1k chars.
Regras de parsing dos PDFs: `pdftotext -layout` separa parágrafos por linha em branco e tabelas rótulo/valor por 2+ espaços; rodapé `Processo nº … - Página N` em toda página; "Saldo devedor … aproximadamente R$" quebra a linha antes do número; a petição segue I – DOS FATOS / II – DO DIREITO / III – DA TUTELA / IV – DOS PEDIDOS / procuração / RG / comprovante de residência.
