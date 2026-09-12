# Memory bank

Estado vivo do projeto em arquivos curtos. É o que um agente ou uma pessoa lê antes de tocar em qualquer coisa, e é o que todo commit que toca código atualiza.

## Ordem de leitura
1. `contexto.md` — o problema, o que é avaliado, o que entregar, quem é dono do quê
2. `arquitetura.md` — como o sistema é hoje e como fica
3. `contratos.md` — interfaces entre api, modelo e extração
4. `features.md` — o que existe, o que está em andamento, quem é dono
5. `decisoes.md` — decisões tomadas e por quê
6. `dados.md` — fatos da base real e regras de parsing

## Regras
- **In-place, não log.** Se uma feature mudou, edite a linha dela. Não escreva "hoje fizemos X" nem datas.
- **Linhas curtas.** Uma ideia por linha. Tabela quando for lista paralela.
- **Estado, não intenção.** `features.md` diz o que está pronto agora. O que falta são as linhas ⬜ de `features.md`; o desenho alvo está em `arquitetura.md`.
- **Todo commit que toca `src/` ou `infra/` edita pelo menos um arquivo daqui.** O hook e a CI bloqueiam se não.
- Arquivo novo aqui só se nenhum existente couber. Adicione-o na ordem de leitura acima.

## Qual arquivo editar
| Mudou | Edite |
|---|---|
| endpoint, tabela, serviço, componente, container, job | `arquitetura.md` e `features.md` |
| assinatura em `src/core`, parâmetro de política | `contratos.md` |
| tecnologia, corte de escopo, regra de negócio | `decisoes.md` |
| descoberta sobre os dados, parsing | `dados.md` |
| dono ou estado de uma feature | `features.md` |
