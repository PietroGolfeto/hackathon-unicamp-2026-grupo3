# data/exemplos

| Conteúdo | Versionado? | Origem e uso |
|---|---|---|
| `sinteticos.csv` | sim | 3.000 processos fictícios amostrados dos modelos do engine (`make sinteticos`), com os cabeçalhos originais das duas abas. Fallback de `make data/train/backtest` e dos testes em `tests/` quando a planilha não está em `data/raw/` |
| `sinteticos_processos.csv` | sim | 340 processos fictícios com autor, advogado, escritório e sinais (300 com decisão simulada em 3 escritórios + 40 no pool da "Banca Demo"). Lido por `make seed-demo` |
| `<numero-cnj>/autos/*.pdf` e `<numero-cnj>/subsidios/*.pdf` | **não** (`.gitignore`) | as 2 pastas de processos exemplo da organização. Copie para cá com o nome da pasta igual ao número CNJ; `make ingest` lê |

Nenhuma linha dos dois CSVs vem da base da Enter. Os nomes dos PDFs de `subsidios/` definem as flags (contrato, extrato, comprovante, dossiê, demonstrativo, laudo).
