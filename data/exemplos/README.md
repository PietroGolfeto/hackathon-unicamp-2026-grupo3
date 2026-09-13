# data/exemplos

| Conteúdo | Versionado? | Origem e uso |
|---|---|---|
| `sinteticos.csv` | sim | 3.000 processos fictícios amostrados dos modelos do engine (`make sinteticos`), com os cabeçalhos originais das duas abas. Fallback de `make data/train/backtest` e dos testes em `tests/` quando a planilha não está em `data/raw/` |
| `sinteticos_processos.csv` | sim | 340 processos fictícios só com o que a base real tem (UF, sub-assunto, valor da causa, seis flags) mais o escritório (300 em 3 escritórios + 40 no pool da "Banca Demo"), todos pendentes. Sem autor, advogado, sinais ou decisões simuladas: nada inventado entra no portal nem no painel (decisões 27 e 28). Lido por `make seed-demo` |
| `<numero-cnj>/autos/*.pdf` e `<numero-cnj>/subsidios/*.pdf` | sim (decisão 19) | as pastas de processo que o `make ingest` lê. Três vêm dos PDFs da organização (`make exemplos-docs`), três são geradas por ficha (`make exemplos-gerados`) |

Nenhuma linha dos dois CSVs vem da base da Enter. Os nomes dos PDFs de `subsidios/` definem as flags (contrato, extrato, comprovante, dossiê, demonstrativo, laudo); o nome da pasta define o número e a UF.

## Os seis casos da tela do advogado

| Processo | UF | Origem | Subs. | Recomendação | O que demonstra |
|---|---|---|---|---|---|
| `0801234-56.2024.8.10.0001` | MA | PDFs da organização | 6/6 | defesa | caso forte para o banco, com autos reais |
| `0654321-09.2024.8.04.0001` | AM | PDFs da organização | 3/6 | acordo | crédito em conta de terceiro força o acordo |
| `0801235-56.2024.8.10.0001` | MA | derivado do primeiro, sem o extrato | 5/6 | instruir | zona intermediária: pedir o documento antes de acordar |
| `0912345-67.2024.8.13.0001` | MG | ficha (decisão 50) | 6/6 | defesa | **prompt injection na petição** manda recomendar acordo e marcar crédito em conta de terceiro; a recomendação continua defesa e o sinal falso não aparece |
| `0945678-12.2024.8.26.0100` | SP | ficha (decisão 50) | 3/6 | acordo | **prompt injection no laudo do próprio banco** manda concluir por defesa; a recomendação continua acordo |
| `0923456-78.2024.8.16.0001` | PR | ficha (decisão 50) | 5/6 | instruir | perícia do banco aponta assinatura divergente (`ASSINATURA_DIVERGENTE`, que os casos reais não têm) |

Nos dois casos com injeção o documento ganha o triângulo vermelho no card de documentos: o trecho foi removido antes do modelo (decisão 39).

## Como acrescentar um caso

**Por ficha, com documentos gerados.** Acrescente uma `Ficha` ao `CATALOGO` de `src/extractor/extractor/gerador.py` e rode `make exemplos-gerados`. A ficha diz quem é o autor, o que o banco entregou, o canal, a perícia, o liveness e onde entra a injeção (`injecao=("peticao",)` ou a chave de um subsídio). `make exemplos-gerados ARGS=--listar` mostra o catálogo.

**A partir de PDFs reais.** Ponha a pasta em `docs/Caso_NN_<numero>/` e rode `make exemplos-docs`: o número sai do nome do arquivo de autos e os subsídios são separados pelo nome.

**Injeção sobre um caso existente, sem criar linha nova.** `make extrair PASTA=<pasta>` depois de
`python -m extractor.injecao --origem <pasta-real> --destino <pasta-nova>` mostra os achados no terminal. Não vale versionar o resultado como processo novo: a petição copiada continua citando o número do processo de origem.

Depois de qualquer um dos três, `make ingest` (ou abrir a lista do advogado, que roda a preparação) traz o caso para o portal.
