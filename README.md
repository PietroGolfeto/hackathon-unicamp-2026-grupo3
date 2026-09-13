# Política de Acordos — Grupo 3 · Hackathon Enter (Unicamp, 12 e 13 de setembro de 2026)

> Aplique IA para resolver, em equipe, um problema real que toda grande empresa do Brasil enfrenta.

Solução do **Grupo 3** para o desafio da Enter: política de acordos do Banco UFMG em processos de empréstimo não
reconhecido. Duas camadas sobre a mesma base de 60 mil sentenças: um **engine de política** (modelo de perda calibrado,
valor esperado, escada de negociação e backtest) e um **portal** onde o advogado vê a recomendação e decide, e o gestor
mede aderência e efetividade.

Relatório técnico completo (política em linguagem jurídica, números, decisões e limitações):
[`docs/relatorio.md`](docs/relatorio.md). Instalação e execução em detalhe: [`SETUP.md`](SETUP.md).

## Como Executar a Solução

```bash
cp .env.example .env
make install       # .venv único (engine, core e api) + npm install do web
```

**Engine de política e backtest** (sem banco, sem Docker):

```bash
make demo          # dados → treino → backtest → testes
make backtest      # replay nos 60k: docs/backtest/resumo.md, gráficos e as tabelas do relatório
make engine-api    # http://localhost:8001/docs  (POST /recomendacao)
```

**Portal completo** (Postgres + API + SPA atrás de um Caddy):

```bash
make up            # sobe db, api e caddy em http://localhost:8080
make jobs-docker   # cria tabelas, seed, carrega o histórico e ingere os processos exemplo
```

Usuários da demonstração (senha `senha123`): `adv1@escritorio-a` (advogado) e `gestor@banco-ufmg` (gestor).

### Variável de ambiente para a extração dos documentos

A leitura dos autos e subsídios chama a OpenAI uma vez por processo, com cache em disco por conteúdo:

```bash
export OPENAI_API_KEY="sua_chave_aqui"
```

Sem a chave, o portal sobe e funciona: o extractor responde do cache e, se não houver cache, a ingestão para com aviso
em vez de inventar leitura dos documentos. O parecer consultivo do painel do gestor fica indisponível.

Os dados da organização não são versionados. Sem eles, tudo roda sobre os CSVs sintéticos gerados por nós em
`data/exemplos/`; com eles, coloque os dois CSVs e a planilha em `data/` conforme o [`SETUP.md`](SETUP.md).

## Como o Sistema Funciona

1. `make backtest` treina e avalia a política nos 60 mil casos e exporta o modelo para `models/*.json`.
2. O portal carrega esse histórico e pontua cada processo pelo modelo do engine.
3. A ingestão lê os PDFs de cada processo em `data/exemplos/<numero>/{autos,subsidios}`.
4. Antes do LLM, o texto passa por uma checagem de segurança e vira um brief determinístico de ~1/3 do tamanho.
5. Uma chamada à OpenAI devolve um resumo em até 5 bullets e as contradições entre a petição e os subsídios.
6. O modelo estima a probabilidade de o banco vencer e a condenação esperada se perder.
7. A política compara o custo esperado de defender com o de acordar e devolve **defesa**, **acordo** (com valor sugerido
   e banda) ou **instruir** (pedir os subsídios que faltam antes de acordar).
8. A recomendação é gravada no momento em que o advogado abre o caso; a decisão dele aponta para ela, e o desvio exige
   justificativa. O painel do gestor mede aderência, efetividade e simula parâmetros da política sobre os 60 mil casos.

### Entradas principais

- `data/Hackaton_Enter_Base_Candidatos.xlsx - *.csv` e `data/raw/*.xlsx`: 60 mil sentenças e os subsídios de cada uma
- `data/exemplos/<numero>/autos/`: autos do processo (petição inicial, procuração, documentos pessoais)
- `data/exemplos/<numero>/subsidios/`: documentos do banco (contrato, extrato, comprovante de crédito, dossiê,
  demonstrativo da dívida, laudo referenciado)
- `src/enteros/policy/policy.yaml`: parâmetros da política (custos, limiares, curva de aceite)

### Saídas principais

- decisão de `defesa`, `acordo` ou `instruir`, com os motivos e a probabilidade de êxito da defesa
- valor sugerido do acordo e a banda mínima/máxima, com escada de abertura, alvo e teto
- resumo do processo em bullets e contradições entre a petição e os subsídios
- minutas de proposta, roteiro de defesa e mensagem à parte adversa
- backtest da política nos 60 mil casos em `docs/backtest/` e aderência e efetividade no painel do gestor

---

_O texto abaixo é do organizador, como veio no template do desafio (edição UFMG, mesmo case). A nossa edição é a da
Unicamp, 12 e 13 de setembro de 2026; os prazos que o time assumiu estão em `memory-bank/contexto.md`._

## Premiação

**R$ 10.000** para a equipe vencedora

---

## 1. Contexto

A **Enter** é uma empresa de Enterprise AI — a maior empresa nativa de IA do país — focada em soluções para processos jurídicos cíveis massificados: casos repetitivos em que pessoas físicas processam grandes empresas (ex: consumidor que processa uma companhia aérea por atraso de voo).

Seu produto principal, o **EnterOS**, é um modelo de operação jurídico onde uma empresa centraliza a gestão de todos os seus escritórios de advocacia, aprimorando a qualidade das peças jurídicas e a produtividade dos advogados. O EnterOS é construído sobre agentes de IA que automatizam e agregam inteligência a todas as etapas de um processo judicial — do recebimento da ação até o encerramento do caso.

---

## 2. Problema: Política de Acordos

O **Banco UFMG** recebe, em média, **~15 mil novos processos por mês**. Desses, cerca de **~5 mil** envolvem um cenário específico: a pessoa que está processando o banco alega que **não reconhece a contratação de um empréstimo** — ela afirma estar sofrendo descontos referentes ao pagamento de um empréstimo que nunca contratou.

Diante de cada processo, o Banco precisa tomar uma decisão estratégica: **defender-se no judiciário ou propor um acordo**.

O fluxo atual funciona assim:

1. Um advogado externo recebe o processo pela plataforma da Enter.
2. Na plataforma, ele acessa os **Autos** (petição inicial, procuração, etc.) e os **Subsídios** (documentos do banco: extrato, contrato, comprovante de crédito, etc.).
3. Com base nesses documentos e na política do banco, decide: **defesa ou acordo?**
4. Se optar por acordo, entra em contato com a parte autora para negociar.
5. Após a decisão, reporta: se optou por acordo ou defesa; o valor proposto; e o resultado da negociação.

O desafio é triplo:
- Definir uma **boa política de acordos**
- Garantir que os advogados a sigam de forma **consistente**
- **Monitorar continuamente** os resultados para avaliar se a política está sendo efetiva

---

## 3. Sua Missão

Construir uma solução que:

- **Defina uma política de acordos** para o Banco UFMG em casos de não reconhecimento de contratação de empréstimo
- **Garanta a implementação** dessa política pelo advogado que está analisando cada caso
- **Monitore os resultados** para avaliar se a política de acordos está sendo efetiva

---

## 4. Requisitos da Solução

A solução deve conter, no mínimo:

| # | Requisito |
|---|-----------|
| 1 | **Regra de decisão** — lógica que analise o processo e determine: acordo ou defesa |
| 2 | **Sugestão de valor** — caso a recomendação seja acordo, sugerir qual valor oferecer |
| 3 | **Acesso à recomendação** — meio prático do advogado acessar a recomendação para o caso que está analisando |
| 4 | **Monitoramento de aderência** — forma do banco acompanhar se a política está sendo seguida pelos advogados |
| 5 | **Monitoramento de efetividade** — forma do banco avaliar se a política está gerando os resultados esperados |

> Fique à vontade para usar quaisquer ferramentas e tecnologias.

---

## 5. O Que Você Está Recebendo

Cada equipe receberá:

- **Chave da OpenAI** com créditos carregados
- **Base de dados** (`.csv`) com o resultado de 60.000 sentenças judiciais dos últimos meses do Banco UFMG em casos de não reconhecimento de contratação de empréstimo (número do caso, valor da causa, resultado, valor de condenação)
- **Base de documentos** (subsídios) disponibilizados pelo Banco UFMG nos últimos 12 meses
- **2 pastas de processos exemplo** para simulação, cada uma contendo:
  - Autos na íntegra (petição inicial, procuração e demais documentos)
  - Subsídios do cliente (documentos de defesa do banco)

### Descrição dos Subsídios

| Documento | Descrição |
|-----------|-----------|
| **Contrato** | Contrato firmado entre o Banco UFMG e a parte autora |
| **Extrato** | Extrato da conta corrente da parte autora com o banco |
| **Comprovante de crédito** | Documento regulatório junto ao BACEN atestando a legitimidade da operação |
| **Dossiê** | Verificação de autenticidade das assinaturas e documentos pessoais do contrato |
| **Demonstrativo de evolução da dívida** | Extrato mês a mês do saldo de dívida e pagamentos |
| **Laudo referenciado** | Síntese da operação de crédito (data, valores, prazos, canal de contratação, etc.) |

---

## 6. Formato de Entrega

Cada equipe deve submeter **neste repositório**:

```
├── src/                  # código-fonte da solução
├── data/                 # dados de exemplo (não inclua dados sensíveis)
├── docs/                 # apresentação final e documentação
│   └── presentation.*    # slides ou documento para a apresentação
├── SETUP.md              # instruções de instalação e execução
└── README.md             # este arquivo (pode ser complementado)
```

Além do repositório, submeter:

1. **Repositório no GitHub** com o código-fonte completo
2. **Arquivos auxiliares** necessários para executar a solução (dependências, setup, dados de exemplo)
3. **Vídeo de até 2 minutos** demonstrando o funcionamento da ferramenta do ponto de vista do advogado
4. **Apresentação** (slides ou outro formato) para a apresentação final — máx. 15 min — cobrindo:
   - Explicação da política de acordos (linguagem acessível ao time jurídico)
   - Potencial financeiro da iniciativa
   - Experiência do usuário advogado
   - Arquitetura e solução técnica
   - Limitações conhecidas da solução
   - Próximos passos (considerando 1 mês adicional de desenvolvimento)

---

## 7. Critérios de Avaliação

| # | Critério | Descrição |
|---|----------|-----------|
| 1 | **Leitura do problema** | Entendimento do caso, priorização correta e impacto no negócio |
| 2 | **Criatividade e usabilidade** | Criatividade na abordagem e qualidade da experiência de uso |
| 3 | **Colaboração** | Divisão de responsabilidades, colaboração e clareza na apresentação |
| 4 | **Execução** | Acurácia do output, funcionalidades embarcadas, consistência e viabilidade |
| 5 | **Uso de IA** | Aplicação de IA para acelerar, melhorar ou diferenciar a solução |

---

## 8. Prazo

| Evento | Data/Hora |
|--------|-----------|
| **Submissão** | 18/04 às **04:00** (da manhã) |
| **Apresentações finais** | 18/04 às **07:00** |

> Boa sorte — e bom café e/ou energético! ☕
