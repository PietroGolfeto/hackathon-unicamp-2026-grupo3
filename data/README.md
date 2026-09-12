# Dados

```
data/
├── raw/                 # NÃO versionado — planilha da Enter e pastas dos 2 processos exemplo
│   ├── Hackaton_Enter_Base_Candidatos.xlsx
│   └── casos/Caso_01_.../*.pdf, Caso_02_.../*.pdf
├── cache/               # NÃO versionado — parquet gerado por `make data`
└── exemplos/
    └── sinteticos.csv   # versionado — 3 mil processos FICTÍCIOS gerados por `make sinteticos`
```

- Nenhum dado da Enter é versionado (regra da organização). O `.gitignore` bloqueia `data/raw/`, `data/cache/`
  e qualquer `.xlsx`/`.csv` fora de `data/exemplos/`.
- `sinteticos.csv` é amostrado dos modelos ajustados (segmentos, razão de condenação), com números CNJ inventados.
  Mantém o schema original (mesmos cabeçalhos das duas abas, já juntas) para o pipeline rodar em clone limpo.
- Com a planilha em `data/raw/`, `make data` usa a base real e o backtest reproduz os números do README.
