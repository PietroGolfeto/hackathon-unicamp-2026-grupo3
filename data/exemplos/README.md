# data/exemplos

| Conteúdo | Versionado? | Origem |
|---|---|---|
| `sinteticos.csv` | sim | gerado por nós: 340 processos fictícios (300 com decisão simulada em 3 escritórios + 40 no pool da "Banca Demo"). Nenhuma linha vem da base da Enter |
| `<numero-cnj>/autos/*.pdf` e `<numero-cnj>/subsidios/*.pdf` | **não** (`.gitignore`) | as 2 pastas de processos exemplo da organização. Copie para cá com o nome da pasta igual ao número CNJ |

`python -m app.cli ingest` lê as pastas; `python -m app.cli seed-demo` lê o CSV. Ambos são idempotentes.
Os nomes dos PDFs de `subsidios/` definem as flags (contrato, extrato, comprovante, dossiê, demonstrativo, laudo).
