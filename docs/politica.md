# Política de acordos — Banco Unicamp (linguagem para o time jurídico)

Aplicação: ações em que a parte autora alega **não reconhecer a contratação de empréstimo consignado** e pede
declaração de inexistência do débito, devolução (em dobro) das parcelas e dano moral. ~5 mil casos/mês.

## A regra em uma frase
**Só vale defender quando o custo esperado de litigar é menor do que o custo esperado de acordar.** O custo de
litigar é a probabilidade de perder × (condenação + honorários de sucumbência + custas + correção até o pagamento)
+ o custo do escritório. O custo de acordar é o valor oferecido × chance de aceite + o custo de litigar se recusarem.
Nenhum desses números é chute: a probabilidade e a condenação vêm de 60 mil sentenças do próprio banco. Para cada caso o
sistema informa o **ponto de indiferença**: a probabilidade de perder a partir da qual acordar fica mais barato (em média
47% no valor-alvo da escada; 26% para uma oferta de 30% do valor da causa). Há uma terceira ação: **instruir** — pedir
ao banco o contrato e/ou o extrato antes de propor o acordo, quando o valor esperado dessa informação supera o custo de
esperar 5 dias.

## O que decide a probabilidade de perder (o que o juiz olha)
| Evidência | Perda quando presente | Perda quando ausente |
|---|---|---|
| **Contrato** assinado/aceito | 13% | 75% |
| **Extrato** com o crédito na conta do autor | 19% | 82% |
| Comprovante de crédito (BACEN) | 20% | 47% |
| Demonstrativo de evolução da dívida | 28% | 39% |
| Dossiê grafotécnico | 30% | 30% |
| Laudo referenciado | 30% | 30% |

Contrato e extrato provam **anuência** e **proveito econômico**; é isso que o Judiciário exige do banco (inversão do
ônus da prova, CDC art. 6º VIII). Dossiê e laudo **não alteram o resultado** — o gasto com perícia terceirizada
não se traduz em êxito. Também pesam: alegação de **golpe** (fraude por terceiro) perde mais que a genérica; e a **UF**
(AM e AP condenam em ~48% dos casos e em ~84% do valor pedido, com 45% de procedência total; MA em 21% e 60%). O valor
da causa **não** muda a chance de perder — só o tamanho da perda. A probabilidade vem com um intervalo de confiança do
modelo; quando ele cruza o ponto de indiferença (2% dos casos), o caso vai para revisão do gestor.

## As três faixas
| Faixa | Quando | O que o advogado faz |
|---|---|---|
| 🟢 **Verde — defender** | Contrato **e** extrato consistentes (crédito na conta do autor). Probabilidade de perda < 15%. ~57% dos casos | Contestação padrão. Se a petição contradiz o extrato ("nunca usou o dinheiro" × TED/PIX/saque), alegar má-fé e pedir condenação em custas |
| 🟡 **Amarela — instruir antes de acordar** | O caso pede acordo, falta contrato **e/ou** extrato, e o valor esperado de pedi-los (chance de o banco localizar × quanto a decisão muda) supera o custo da busca e dos 5 dias de espera. Um documento sozinho raramente basta; **o par contrato + extrato** costuma virar o caso para defesa | Solicitar os subsídios ao banco com prazo de **5 dias**. Vieram → reavaliar (normalmente vira verde). Não vieram → acordar, sabendo que a chance de perder é maior do que parecia |
| 🔴 **Vermelha — acordar já** | Probabilidade de perda > 60% **ou** sinal grave: crédito em **conta de terceiro**, **biometria/liveness ausente** em canal digital, documento presente mas inconsistente. ~24% dos casos, ~59% do custo | Propor acordo **na primeira oportunidade** (antes da contestação, poupando honorários e tempo), seguindo a escada abaixo. Sinal grave não espera documento |

Quando a recomendação é defender e falta algum subsídio, o sistema lista o que pedir ao banco **em paralelo**, sem
atrasar a contestação: recuperar o documento barateia a defesa, mas não muda a decisão.

## A escada de negociação (quando acordar)
A proposta não é um número solto; é **cancelamento do contrato + baixa do saldo devedor + devolução simples das
parcelas descontadas + indenização**. O sistema entrega três valores:

- **Abertura** — primeira proposta (alvo com 20% de desconto).
- **Alvo** — o valor que minimiza o custo esperado, considerando a chance de aceite (âncora: os 280 acordos históricos
  fecharam entre 20% e 40% do valor da causa, mediana 29%).
- **Teto (walk-away)** — nunca acima de 90% do custo esperado de litigar (descontado o saldo devedor que será baixado)
  nem de 70% do valor da causa. Contraproposta acima do teto: **defender**.

Piso: nunca abaixo da devolução simples das parcelas já descontadas (ninguém aceita menos do que perdeu).

## Regras de ouro
1. **Nunca acima do teto.** Acordo acima do custo esperado de litigar é prejuízo certo.
2. **A política não é divulgada.** Se a parte autora souber o teto, a oferta vira o teto. Mesmo advogado com muitas
   ações contra o banco: defender primeiro.
3. **Toda decisão é registrada contra a recomendação que o advogado viu.** Divergir é permitido, mas exige
   justificativa com código; o resultado da negociação (aceito, recusado, contraproposta, valor final) é obrigatório.
4. **O documento que não prova o que deveria não conta.** Extrato com crédito em conta que não é do autor vale como
   extrato ausente.

## Exemplos
- **Caso 01 (São Luís/MA)**: 6 subsídios, dossiê conforme (assinatura 91%, biometria 97%), extrato com o crédito e
  TED para conta da própria autora. Perda estimada 1,1% (IC 1,0–1,3%). **Defender.** A petição afirma que a autora "jamais utilizou
  os valores" — o extrato prova o contrário.
- **Caso 02 (Manaus/AM)**: sem contrato, sem extrato, crédito caiu em conta da Caixa que o autor diz não ter,
  liveness não localizado, BO e reclamação no BACEN. Perda estimada 98% (IC 97–98%); custo esperado de litigar ≈ R$ 33 mil
  (incluindo o saldo de R$ 2.748 que será baixado). Os sinais graves **forçam acordo**: abrir em R$ 9 mil, alvo R$ 11.250
  (devolução de R$ 1.440 + baixa do saldo + indenização), teto R$ 17,5 mil.
- **Caso 02 sem os sinais da IA** (só as flags dos subsídios): mesma probabilidade, mas a recomendação vira **instruir**:
  pedir contrato (chance de localizar 50%) e extrato (69%) em 5 dias — valor esperado da informação ≈ R$ 3,8 mil, chance de
  achar os dois 34%; se vierem, a perda estimada cai para ~10% e o caso vira defesa; se não vierem, acordar.
