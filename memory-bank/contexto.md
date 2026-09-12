# Contexto

## O problema
O Banco UFMG recebe ~15 mil processos por mês; ~5 mil são "não reconheço este empréstimo". Para cada um, o advogado externo decide: defender no judiciário ou propor acordo. O banco precisa de uma política de acordos, garantir que os advogados a sigam e medir se ela funciona.

## Requisitos mínimos (todos obrigatórios)
| # | Requisito | Como atacamos |
|---|---|---|
| 1 | Regra de decisão acordo/defesa | política de custo esperado sobre os scores do modelo |
| 2 | Valor sugerido de acordo | oferta alvo + banda mín/máx |
| 3 | Acesso prático do advogado | portal web, link direto por caso, resumo copiável |
| 4 | Monitoramento de aderência | decisão gravada contra a recomendação que o advogado viu; desvio exige justificativa |
| 5 | Monitoramento de efetividade | resultado real da negociação + backtest da política nos 60 mil casos |

## Critérios de avaliação
Leitura do problema · Criatividade e usabilidade · Colaboração · Execução · Uso de IA.

## Entregáveis
Repo público com `src/`, `data/` (exemplos, sem dado sensível), `docs/` (apresentação), `SETUP.md`, `README.md`. Vídeo de até 2 min do ponto de vista do advogado. Apresentação de até 15 min cobrindo: política em linguagem jurídica, potencial financeiro, experiência do advogado, arquitetura, limitações, próximos passos com 1 mês.

## Prazo (assumido igual à edição anterior; confirmar com a organização)
Submissão 13/09 04:00 · Apresentações 13/09 07:00 · Freeze de código 02:00 · Vídeo gravado até 01:00 · API congelada (só mudanças aditivas) a partir da hora 10 do evento.

## Time e donos
| Papel | Pessoa | Pastas | Apresenta |
|---|---|---|---|
| P1 modelo | (nome) | `src/model` | política em linguagem jurídica, potencial financeiro |
| P2 backend, front básico, deploy | Lucas | `src/api`, `src/core`, `src/web` (base), `infra`, `.github`, `scripts` | arquitetura |
| P3 LLM e documentos | (nome) | `src/extractor` | uso de IA |
| P4 portal do advogado, vídeo | (nome) | `src/web/src/pages/advogado`, `docs/video.*` | experiência do advogado |
| P5 painel do gestor, deck | (nome) | `src/web/src/pages/gestor`, `docs/`, `SETUP.md` | abertura, limitações, próximos passos |

## Referências
Vencedor da edição anterior (mesmo case): https://github.com/DataCaio/hackathon-ufmg-2026-exit · Regras: https://www.hackathon.getenter.ai/regras · Plano completo: `docs/plano-implementacao.md`
