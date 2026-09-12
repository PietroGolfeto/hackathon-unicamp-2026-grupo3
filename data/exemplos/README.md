# data/exemplos

| Conteúdo | Versionado? | Origem e uso |
|---|---|---|
| `sinteticos.csv` | sim | 3.000 processos fictícios amostrados dos modelos do engine (`make sinteticos`), com os cabeçalhos originais das duas abas. Fallback de `make data/train/backtest` e dos testes em `tests/` quando a planilha não está em `data/raw/` |
| `sinteticos_processos.csv` | sim | 340 processos fictícios só com o que a base real tem (UF, sub-assunto, valor da causa, seis flags) mais o escritório (300 em 3 escritórios + 40 no pool da "Banca Demo"), todos pendentes. Sem autor, advogado, sinais ou decisões simuladas: nada inventado entra no portal nem no painel (decisões 27 e 28). Lido por `make seed-demo` |
| `<numero-cnj>/autos/*.pdf` e `<numero-cnj>/subsidios/*.pdf` | **não** (`.gitignore`) | as 2 pastas de processos exemplo da organização. Copie para cá com o nome da pasta igual ao número CNJ; `make ingest` lê |

Nenhuma linha dos dois CSVs vem da base da Enter. Os nomes dos PDFs de `subsidios/` definem as flags (contrato, extrato, comprovante, dossiê, demonstrativo, laudo).
