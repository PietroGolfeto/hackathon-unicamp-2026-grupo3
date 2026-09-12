# data/

Nada da Enter é versionado aqui (decisão 19 em `memory-bank/decisoes.md`). Coloque os arquivos assim:

```
data/
├── Hackaton_Enter_Base_Candidatos.xlsx - Resultados dos processos.csv      # 60.000 sentenças
├── Hackaton_Enter_Base_Candidatos.xlsx - Subsídios disponibilizados.csv    # 6 flags por processo
├── exemplos/
│   ├── README.md                      # versionado
│   ├── sinteticos.csv                 # versionado: 340 processos fictícios nossos (seed-demo)
│   └── <numero-cnj>/                  # ignorado: as 2 pastas de processos exemplo
│       ├── autos/*.pdf
│       └── subsidios/*.pdf            # o nome do arquivo define a flag (contrato, extrato, …)
└── derived/                           # ignorado: saídas de P1/P3 (historico_scored.csv, extraidos/, scores/)
```

`make historico` carrega os CSVs; `make ingest` lê `exemplos/<numero>/`; `make seed-demo` lê `sinteticos.csv`. Sem os CSVs a API sobe normalmente e só a simulação da política fica desabilitada.
