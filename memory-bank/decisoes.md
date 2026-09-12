# Decisões

Formato: número, decisão, por quê. Decisão revertida: edite a linha dizendo o que a substituiu; não apague.

1. **FastAPI + SQLAlchemy 2 + Postgres 16.** Mesmo runtime do XGBoost; P1 e P3 plugam funções Python sem serviço extra.
2. **React 19 + Vite + TypeScript + Mantine + TanStack Query, SPA separada da API.** Fácil de dividir por páginas entre três pessoas; Mantine dá tabela, form e card sem configurar CSS.
3. **Scores ≠ política.** Modelo grava scores uma vez; política é função pura versionada. Permite simular parâmetros nos 60k em tempo real e medir aderência contra o que o advogado viu.
4. **Backtest com resultados reais dos 60k**, não com previsão. Número do slide financeiro fica defensável; baselines "defender tudo" e "acordar tudo" sempre ao lado.
5. **Extinção fica no backtest** como custo real de defender com condenação zero (toggle). Para treino, P1 decide. O vencedor anterior descartou; excluir 23% da base enviesaria o baseline.
6. **Sinais extraídos dos autos entram pela política (`sinais_forcam_acordo`), não pelo modelo.** O histórico não tem esses rótulos; vender como feature treinada seria desonesto.
7. **8 tabelas, negociação como colunas em `decisoes`, sem Alembic.** Uma pessoa no backend; `make reset` recria.
8. **Recomendação gravada ao abrir o caso; decisão aponta para ela.** Aderência mede contra o que o advogado viu, mesmo se a política mudar depois.
9. **`decisoes` append-only; atual = mais recente.** Dois jurados no mesmo caso não podem ver erro de conflito.
10. **IDs inteiros nas URLs.** Número CNJ tem pontos e quebra o fallback do SPA em servidor estático.
11. **Um Caddy, mesma origem.** Sem CORS, cookie funciona sem configuração, um container a menos.
12. **VPS primário; homelab é standby permanente em subdomínio próprio via túnel.** Internet residencial e troca de DNS às 07:00 são riscos que não valem a pena.
13. **Link mágico `/demo?t=` para a banca.** Ninguém digita senha no celular; cada jurado recebe um caso distinto.
14. **Fora de escopo:** cadastro/recuperação de senha, websockets (poll de 5 s), fila, upload, RAG, fine-tuning, Kubernetes, segundo frontend.
15. **Commits pequenos com TL;DR; memory-bank atualizado in-place em todo commit de código; CI bloqueia.** Cinco pessoas com IA precisam de um único estado compartilhado.
16. **Sem atribuição de IA em commits, PRs, código ou docs.** Ruído; autoria é do time.
17. **Nomes de domínio em português** (`processo`, `recomendacao`, `decisao`); termos técnicos genéricos em inglês (`router`, `service`, `client`).
18. **Dependência nova só com uma linha aqui.** Controle do que entra no compose e no tempo de build.
19. **Nenhum dado da Enter no repo:** nem os CSVs brutos, nem `data/processos_exemplo/`, nem derivados que carreguem as linhas (histórico com scores). Versionar só o que é nosso e pequeno: modelo treinado exportado em JSON/UBJ do XGBoost em `src/model/artifacts/`, resumo agregado do backtest da política ativa, e um CSV de processos sintéticos gerado por nós em `data/exemplos/sinteticos.csv`. Por quê: regra explícita da organização, a banca já tem os dados e o `SETUP.md` diz onde colocar. PDFs dos processos exemplo: perguntar aos organizadores antes de versionar.
20. **Pacote Python compartilhado chama-se `core` e mora em `src/core/core/`.** Projeto pip em `src/core`, import `from core import ...`.
