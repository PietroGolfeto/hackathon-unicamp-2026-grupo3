# CLAUDE.md — como trabalhar neste repositório

Lido por qualquer agente de IA (Claude Code, Cursor, Copilot) e por qualquer pessoa antes de tocar no código. Cinco pessoas usando IA precisam produzir um sistema só. Este arquivo e o `memory-bank/` são o que garante isso.

## Antes de qualquer tarefa
1. Leia `memory-bank/README.md` e depois todos os arquivos de `memory-bank/`. São curtos e são o estado atual do projeto.
2. Leia `docs/plano-implementacao.md` só se for construir algo que ainda não existe.
3. Rode `make hooks` uma vez por clone. Instala as verificações locais de commit.

## O que estamos construindo
Política de acordos do Banco UFMG para processos de empréstimo não reconhecido: API + portal do advogado + painel do gestor, com modelo (P1) e extração de documentos (P3) plugados por contratos em `src/core`. Detalhes em `memory-bank/contexto.md`.

## Stack fixa
Python 3.12 · FastAPI · SQLAlchemy 2 · Postgres 16 · React 19 + Vite + TypeScript · Mantine · TanStack Query · docker compose · Caddy. Não proponha trocar. Dependência nova só com uma linha em `memory-bank/decisoes.md`.

## Pastas e donos
| Pasta | Dono | Conteúdo |
|---|---|---|
| `src/core` | Lucas (P2) | contratos, política, parsing. Muda só com `memory-bank/contratos.md` |
| `src/api` | Lucas (P2) | FastAPI, jobs de carga |
| `src/web` | Lucas (P2) base; P4 `pages/advogado`; P5 `pages/gestor` | SPA |
| `src/model` | P1 | modelo e scores |
| `src/extractor` | P3 | extração LLM, análise, minutas |
| `infra`, `.github`, `scripts`, `Makefile` | Lucas (P2) | compose, deploy, CI |
| `docs`, `SETUP.md`, `README.md` | P5 | apresentação e instruções |
| `memory-bank` | todos | estado vivo do projeto |

Não edite pasta de outro sem combinar. Mudança cruzada vai em PR pequeno com o dono marcado.

## Regras de colaboração

### 1. Commit pequeno e inteligível
Um commit resolve uma coisa. Limite: 20 arquivos e 800 linhas (lockfiles, CSV, PDF e imagens não contam). Se precisar passar disso com justificativa, termine o assunto com `[grande]`. A CI bloqueia o resto.

### 2. Mensagem com TL;DR
Primeira linha: `<area>: <o que muda, em uma frase>`, até 72 caracteres, em português.
Áreas: `api` `web` `core` `model` `extractor` `infra` `docs` `ci` `chore` `data` `scripts`. Escopo opcional: `api(auth): ...`.
Corpo opcional e curto: o porquê e o que observar. Sem trailers de ferramenta.

```
api: grava recomendação ao abrir o caso, sob a política ativa

A decisão do advogado passa a apontar para a recomendação que ele viu.
Aderência é medida contra ela mesmo se a política mudar depois.
```

### 3. Todo commit de código atualiza o memory-bank, in-place
Tocou `src/` ou `infra/`? No mesmo commit, edite pelo menos `memory-bank/arquitetura.md` ou `memory-bank/features.md`. Edite a linha da feature; não adicione histórico nem datas. `memory-bank/README.md` diz qual arquivo editar para cada tipo de mudança. Hook e CI bloqueiam commit de código sem isso.

### 4. Nunca versionar
`.env` (só `.env.example`), os CSVs da Enter em `data/`, `data/processos_exemplo/`, artefatos de modelo (`*.joblib`, `*.pkl`), `node_modules`, chaves. `scripts/check_secrets.sh` bloqueia.

### 5. Contratos e API
`src/core` é a fronteira entre api, model e extractor. Mudança lá exige editar `memory-bank/contratos.md` no mesmo commit e avisar no grupo. Depois do congelamento da API (hora 10, ver `memory-bank/contexto.md`), só mudanças aditivas: campo novo, endpoint novo. Nunca renomear ou remover.

### 6. Antes de commitar
`make check` roda o mesmo que a CI. Com `make hooks` instalado, o essencial roda sozinho no commit.

### 7. Sem atribuição de IA
Nada de `Co-Authored-By: <modelo>`, "Generated with", emoji de robô ou similares em commits, PRs, código ou docs. A CI bloqueia. Autoria é do time.

### 8. Branch e PR
Branch curta, PR pequeno para `main`, CI verde antes do merge, template de PR preenchido. Em emergência de madrugada, push direto em `main` é aceitável se `make check` passou localmente.

## Como um agente deve trabalhar aqui
- Leia o memory-bank antes de propor qualquer coisa. Não re-derive decisões já registradas em `decisoes.md`.
- Faça a tarefa pedida no menor diff que a resolve. Não refatore fora do escopo, não "aproveite para" melhorar outra coisa.
- Reutilize o que existe em `src/core` antes de criar utilitário novo.
- Termine cada passo com `make check`. Não deixe teste quebrado para o próximo.
- Ao finalizar, atualize o memory-bank no mesmo commit e escreva a mensagem no formato acima.
- Se a tarefa exigir mudar um contrato ou uma decisão, pare e diga isso em vez de contornar.
- Nunca rode `make reset` (apaga o banco) apontando para a VPS.

## Convenções de código
**Python**: 3.12, type hints em tudo, pydantic v2 para dados que cruzam fronteira, SQLAlchemy 2 estilo `Mapped[...]`, `ruff` com linha 100. Funções pequenas. Nomes de domínio em português (`processo`, `recomendacao`, `decisao`), termos técnicos em inglês (`router`, `service`, `client`). Erros de API via `HTTPException` com `detail` legível pelo usuário.
**TypeScript**: `strict`, componentes funcionais, dados via TanStack Query, UI via Mantine, formatação de dinheiro e data só em `src/web/src/lib/format.ts`. Sem CSS solto além do que Mantine oferece.
**Testes**: `pytest` em `tests/` ao lado do pacote, com valores reais da base sempre que possível. Front: lint e build são o teste mínimo.
**Português** em commits, docs, nomes de domínio e mensagens ao usuário.

## Comandos
| Comando | O que faz |
|---|---|
| `make hooks` | instala hooks de commit neste clone |
| `make check` | tudo que a CI roda: segredos, memory-bank, commits, testes |
| `make test` | testes dos componentes que existirem |
| `make up` / `make down` | sobe e derruba com docker compose (quando `infra/` existir) |
| `make reset` | recria banco e roda seed (local, nunca na VPS) |
