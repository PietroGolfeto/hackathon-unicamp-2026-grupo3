# Política de acordos — Banco Unicamp (linguagem para o time jurídico)

Aplicação: ações em que a parte autora alega **não reconhecer a contratação de empréstimo consignado** e pede
declaração de inexistência do débito, devolução (em dobro) das parcelas e dano moral. ~5 mil casos/mês.

## A regra em uma frase
**Só vale defender quando o custo esperado de litigar é menor do que o custo esperado de acordar.** O custo de
litigar é a probabilidade de perder × (condenação + honorários de sucumbência + custas + correção até o pagamento)
+ o custo do escritório. O custo de acordar é o valor oferecido × chance de aceite + o custo de litigar se recusarem.
Nenhum desses números é chute: a probabilidade e a condenação vêm de 60 mil sentenças do próprio banco.

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
(AM e AP condenam em ~50% dos casos e em ~84% do valor pedido; MA em 21% e 60%).

## As três faixas
| Faixa | Quando | O que o advogado faz |
|---|---|---|
| 🟢 **Verde — defender** | Contrato **e** extrato consistentes (crédito na conta do autor). Probabilidade de perda < 15%. ~57% dos casos | Contestação padrão. Se a petição contradiz o extrato ("nunca usou o dinheiro" × TED/PIX/saque), alegar má-fé e pedir condenação em custas |
| 🟡 **Amarela — instruir antes de decidir** | Falta contrato **ou** extrato, mas o documento pode existir no banco. Recuperá-lo derruba o custo esperado em mais de 10% do valor da causa | Solicitar o subsídio ao banco com prazo de **5 dias**. Veio → reavaliar (normalmente vira verde). Não veio → vermelha |
| 🔴 **Vermelha — acordar já** | Probabilidade de perda > 60% **ou** sinal grave: crédito em **conta de terceiro**, **biometria/liveness ausente** em canal digital, documento presente mas inconsistente. ~24% dos casos, ~60% do custo | Propor acordo **na primeira oportunidade** (antes da contestação, poupando honorários e tempo), seguindo a escada abaixo |

## A escada de negociação (quando acordar)
A proposta não é um número solto; é **cancelamento do contrato + baixa do saldo devedor + devolução simples das
parcelas descontadas + indenização**. O sistema entrega três valores:

- **Abertura** — primeira proposta (alvo com 20% de desconto).
- **Alvo** — o valor que minimiza o custo esperado, considerando a chance de aceite (âncora: os 280 acordos históricos
  fecharam entre 20% e 40% do valor da causa, mediana 29%).
- **Teto (walk-away)** — nunca acima de 90% do custo esperado de litigar nem de 70% do valor da causa. Contraproposta
  acima do teto: **defender**.

Piso: nunca abaixo da devolução simples das parcelas já descontadas (ninguém aceita menos do que perdeu).

## Regras de ouro
1. **Nunca acima do teto.** Acordo acima do custo esperado de litigar é prejuízo certo.
2. **A política não é divulgada.** 23% das ações terminam em extinção — sinal de litigância em massa. Mesmo advogado
   com muitas ações contra o banco: defender primeiro.
3. **Toda decisão é registrada contra a recomendação que o advogado viu.** Divergir é permitido, mas exige
   justificativa com código; o resultado da negociação (aceito, recusado, contraproposta, valor final) é obrigatório.
4. **O documento que não prova o que deveria não conta.** Extrato com crédito em conta que não é do autor vale como
   extrato ausente.

## Exemplos
- **Caso 01 (São Luís/MA)**: 6 subsídios, dossiê conforme (assinatura 91%, biometria 97%), extrato com o crédito e
  TED para conta da própria autora. Perda estimada 0,9%. **Defender.** A petição afirma que a autora "jamais utilizou
  os valores" — o extrato prova o contrário.
- **Caso 02 (Manaus/AM)**: sem contrato, sem extrato, crédito caiu em conta da Caixa que o autor diz não ter,
  liveness não localizado, BO e reclamação no BACEN. Perda estimada 97%; custo esperado de litigar ≈ R$ 30 mil.
  **Acordar**: abrir em R$ 9 mil, alvo R$ 11 mil (devolução de R$ 1.440 + baixa de R$ 2.748 de saldo + indenização),
  teto R$ 17,5 mil.
