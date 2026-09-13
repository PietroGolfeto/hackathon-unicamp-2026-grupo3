# Vídeo de 2 minutos — ponto de vista do advogado

Regra da entrega: **até 2 min**, demonstrando a ferramenta **do ponto de vista do advogado**. Sem slides, sem
arquitetura, sem painel do gestor como assunto — é uma gravação de tela do portal, narrada em primeira pessoa por quem
usa. Alvo: **1min50**, para caber com folga.

## O fio condutor (a única coisa que o jurado tem que levar do vídeo)
> Três casos, três respostas diferentes — e a terceira resposta ("peça o documento antes") ninguém mais tem.
> O sistema não dá uma nota: dá a conta, o valor da oferta e o que fazer, antes de eu abrir um PDF.

Os três casos que aparecem na lista servem exatamente a isso (`memory-bank/decisoes.md` 45):

| Ordem | Caso | Resposta | Por quê |
|---|---|---|---|
| 1 | `0801234-56.2024.8.10.0001` — São Luís/MA | 🟢 **Defender** | 6/6 subsídios, extrato com o crédito e a TED para a conta da autora |
| 2 | `0654321-09.2024.8.04.0001` — Manaus/AM | 🔴 **Acordar** | sem contrato, sem extrato, crédito em conta de terceiro |
| 3 | `0801235-56.2024.8.10.0001` — o caso 1 **sem o extrato** | 🟡 **Instruir** | um documento a menos vira a decisão |

O caso 3 é o caso 1 com um documento a menos. **Diga isso no vídeo** — é honesto e é o melhor momento da demo: mostra
que a recomendação reage à prova, não ao chute.

---

## Antes de gravar (15 min, não pule)

1. `OPENAI_API_KEY` no `.env` **e cache do extractor quente**. Sem extração, os sinais somem e os três casos viram
   "instruir" — a demo inteira morre (decisão 45).
2. Rode `make reset` e abra a lista **uma vez** para a preparação rodar (~1 min por caso na primeira vez; depois vem do
   cache em disco e é instantâneo — decisão 47). O cache sobrevive ao reset.
3. `make reset-demo` entre uma tomada e outra: apaga decisões e recomendações, mantém os processos. É o botão de "de novo".
4. Janela do navegador limpa: sem barra de favoritos, sem extensões, uma aba só, zoom 110–125%, 1920×1080.
5. Ensaie uma vez com cronômetro. Se passar de 2:00, corte o bloco 2, não o bloco 5.
6. Confira na tela os números que você vai falar (probabilidade, custo, escada). Se mudaram, ajuste a fala — número
   falado diferente do número da tela é o tipo de coisa que jurado nota.

---

## O roteiro

**302 palavras de narração ≈ 1min53 a 160 palavras por minuto**, mais a cartela. Cronometre o seu ritmo lendo o bloco 1:
se ele passar de 11 s, você fala mais devagar que isso — corte então as frases marcadas com **✂️**, que valem ~30
palavras (≈ 12 s) e não tiram nada essencial.

### 0:00 – 0:11 · Tela: lista de casos já aberta
> Sou advogado externo do Banco Unicamp. Chegam cinco mil ações por mês dizendo a mesma coisa: "não reconheço esse
> empréstimo". Em cada uma, eu decido: defender ou propor acordo?

### 0:11 – 0:24 · Tela: passa o mouse pela lista, mostra a coluna de subsídios
> A fila já vem pronta: número, valor da causa e quais dos seis subsídios o banco entregou. ✂️ Sem contrato e sem
> extrato, o caso é grave. Abro o primeiro.

### 0:24 – 0:47 · Tela: caso 1. Cartão de recomendação → cartão da IA
> Antes de eu abrir um único PDF, o sistema já respondeu: **defender**. Chance de êxito de quase cem por cento, com a
> conta ao lado: quanto custa defender e quanto custaria acordar.
>
> E a IA já leu os autos por mim — cinco linhas. Achou a contradição: a petição diz que a autora nunca usou o dinheiro;
> o extrato mostra a TED para a conta dela. Essa é a minha contestação.

*Ação de tela:* abra **um** PDF em nova aba por 2 segundos e volte. Prova que os autos são reais.

### 0:47 – 1:16 · Tela: caso 2. Cartão vermelho → banda de oferta → registra decisão
> Caso dois, Manaus. Vermelho: **acordar**. Sem contrato, sem extrato, e o crédito caiu na conta de um terceiro — esse
> sinal sozinho já força o acordo.
>
> E não é um número solto: abro em nove mil, alvo onze mil e duzentos e cinquenta, teto dezessete e meio. Acima do teto,
> eu defendo.
>
> Registro a decisão — ✂️ e já sai a minuta da proposta e a mensagem para o advogado do autor.

### 1:16 – 1:36 · Tela: caso 3 (o caso 1 sem o extrato)
> Terceiro caso: é o primeiro, **sem o extrato bancário**. Só isso, e a recomendação muda. Não é defender nem acordar: é
> pedir o extrato ao banco e decidir em cinco dias — porque esperar esse documento vale mais do que acordar hoje. Se ele
> vier, o caso volta a ser defesa.

### 1:36 – 1:52 · Tela: registra o resultado da negociação; 2 s no painel do gestor
> Quando a negociação fecha, eu registro o resultado. Tudo fica gravado contra a recomendação que eu vi — o banco mede
> aderência e efetividade ✂️ e a política aprende com cada acordo.
>
> Nos sessenta mil processos do banco, essa régua custa cento e seis milhões a menos.

### 1:52 – 1:56 · Cartela final (sem narração, 4 s)
```
Política de Acordos · Banco Unicamp — Grupo 3
−31% no custo dos 60 mil processos · 3 respostas, não 2
<url da demo>   ·   <url do repo>
```

---

## Cortes opcionais (só se sobrar tempo; cada um custa 5–8 s)
- **Documento suspeito**: o triângulo vermelho no card de documentos, com a fala "esse PDF tinha instrução escondida
  tentando conversar com a IA; o sistema removeu e me avisou". Impressiona, mas só entra se o vídeo estiver em 1:45.
- **Divergir da recomendação**: escolher o contrário e a justificativa obrigatória aparecendo. Mostra governança em 6 s.
- **Cronômetro**: "o caso inteiro levou quarenta segundos" — só se a tomada realmente for rápida.

## Como gravar
- **Narração separada da tela.** Grave o áudio primeiro (celular no gravador de voz já basta, ambiente sem eco), depois
  a tela seguindo o áudio. Sai muito melhor do que narrar ao vivo e tentar acertar os cliques.
- **Legenda queimada no vídeo.** Boa parte dos jurados assiste sem som na primeira passada.
- **Mouse devagar**, movimentos retos, sem ficar procurando o botão. Ensaie o caminho de cliques até ele ficar mecânico.
- **Corte tempo morto**: qualquer espera acima de 1 s vira corte seco. Nada de transição bonita.
- **Uma voz só**, primeira pessoa, presente. Nunca "o nosso sistema faz"; sempre "eu abro", "eu registro", "eu defendo".
- Formato: MP4 1080p, arquivo no `docs/` (ou link não listado no YouTube, se o tamanho pesar no repo).

---

## Onde o vídeo ganha ponto (critérios da Enter)

| Critério | O que o vídeo precisa mostrar | Onde está no roteiro |
|---|---|---|
| **Leitura do problema** | que a decisão é econômica, não jurídica: a conta aparece ao lado da recomendação | 0:24 e 0:47 |
| **Criatividade e usabilidade** | a terceira resposta ("instruir") e a escada de oferta com teto | 0:47 e 1:16 |
| **Execução** | é um produto que roda, com autos de verdade e PDF abrindo | 0:24 (abrir o PDF) |
| **Uso de IA** | a IA leu os autos e achou a contradição — não é chatbot, é insumo da decisão | 0:24 |
| **Colaboração** | **não cabe no vídeo.** Vai no deck (ver abaixo) | — |

---

## O que mais fazer para vencer (fora do vídeo, em ordem de retorno)

1. **Subir a VPS e o link `/demo` funcionando no celular do jurado.** É o item 🔧 de maior risco hoje e o que mais move
   "execução" e "usabilidade": jurado que usa lembra; jurado que assiste esquece. Teste o link num celular com 4G, não
   no wi-fi da sala.
2. **`SETUP.md` e `README.md` que rodam em 5 minutos** num clone limpo (hoje ⬜ com P5). Um jurado técnico tenta rodar.
   Se rodar de primeira, vale mais que um slide.
3. **Um slide de colaboração — quase ninguém faz.** É critério explícito e vocês têm a melhor história possível: cinco
   pessoas, cinco IAs, um `CLAUDE.md`, um `memory-bank` e uma CI que **bloqueia** commit que toca código sem atualizar o
   estado do projeto. Mostre o hook barrando um commit; é 20 segundos e ninguém mais tem.
4. **Slide "por que não é um limiar de 0,60"** — a comparação direta com o que o vencedor anterior fez: limiar fixo
   economiza 24,8%, custo esperado com três respostas economiza 31,0%, o oráculo economiza 44,3%. Mesmos dados, mesma
   régua de custos, só a regra muda. É a sua vitória em uma tabela (`docs/relatorio.md`, tabela C).
5. **O slide de honestidade.** "O lado defesa é fato; o lado acordo é hipótese de aceite — de 17% a 31% conforme o quanto
   os autores aceitam." Bancas de hackathon são treinadas a desconfiar do número grande; quem declara a premissa antes de
   ser perguntado ganha a pergunta.
6. **Fechar o ciclo de efetividade na demo ao vivo**: registrar um resultado de negociação e mostrar o painel do gestor
   mudando. Era exatamente o ponto fraco do vencedor anterior (efetividade medida como métrica de modelo, não como
   resultado real).
7. **Plano B para a apresentação**: o vídeo gravado + um GIF de 20 s de cada tela salvos localmente. Se a VPS cair às
   07:00, a apresentação continua sem uma palavra sobre isso.
8. **Grave o vídeo cedo** (meta: 01:00, conforme `docs/plano-implementacao.md`). Vídeo gravado às 03:00 é vídeo ruim, e
   é o único entregável que não dá para consertar na apresentação.
