# data/

Nada da Enter é versionado aqui (decisão 19 em `memory-bank/decisoes.md`). Coloque os arquivos assim:

```
data/
├── Hackaton_Enter_Base_Candidatos.xlsx - Resultados dos processos.csv      # portal: 60.000 sentenças
├── Hackaton_Enter_Base_Candidatos.xlsx - Subsídios disponibilizados.csv    # portal: 6 flags por processo
├── raw/                                                                    # engine: planilha bruta (ignorado)
│   └── Hackaton_Enter_Base_Candidatos.xlsx
├── cache/                             # engine: parquet gerado por `make data` (ignorado)
├── exemplos/
│   ├── README.md                      # versionado
│   ├── sinteticos.csv                 # versionado: 3 mil processos fictícios gerados pelos modelos (`make sinteticos`); schema das duas abas
│   ├── sinteticos_processos.csv       # versionado: 340 processos fictícios com autor, advogado e escritório (`make seed-demo`)
│   └── <numero-cnj>/                  # ignorado: as 2 pastas de processos exemplo
│       ├── autos/*.pdf
│       └── subsidios/*.pdf            # o nome do arquivo define a flag (contrato, extrato, …)
└── derived/                           # ignorado: saídas de P1/P3 para o portal (historico_scored.csv, extraidos/, scores/)
```

Dois consumidores da mesma base:
- **Portal e API** (`src/api`): `make historico` lê os **2 CSVs**; `make ingest` lê `exemplos/<numero>/`; `make seed-demo` lê `sinteticos_processos.csv`. Sem os CSVs a API sobe e só a simulação da política fica desabilitada.
- **Engine e backtest** (`src/enteros`): `make data/train/backtest` leem a **planilha** em `raw/`; sem ela rodam sobre `sinteticos.csv` (números ilustrativos).
