"""Minutas por template (sem LLM): proposta de acordo, roteiro de defesa e mensagem ao advogado adverso.

Dependem da recomendação da política, por isso não entram no cache do LLM. Texto em linguagem
jurídica, com os valores da recomendação e o que foi extraído dos autos; o advogado revisa antes de usar.
"""

from __future__ import annotations

from core.caso import NOMES_SUBSIDIOS, CasoFeatures
from core.docs import DadosExtraidos, Minutas
from core.politica import Recomendacao, brl

ORIGEM = "template"


def _tratamento(dados: DadosExtraidos) -> str:
    adv = dados.advogado_autor
    if adv.nome:
        return f"{adv.nome}" + (f" (OAB {adv.oab})" if adv.oab else "")
    return "advogado(a) da parte autora"


def _autor(dados: DadosExtraidos) -> str:
    return dados.autor.nome or "a parte autora"


def _provas(caso: CasoFeatures, dados: DadosExtraidos) -> list[str]:
    itens = [NOMES_SUBSIDIOS[k] for k in caso.subsidios.presentes()]
    c = dados.contrato
    if c.assinatura in ("fisica", "digital", "biometria"):
        itens.append({"fisica": "assinatura manuscrita no contrato", "digital": "aceite eletrônico registrado",
                      "biometria": "biometria facial no ato da contratação"}[c.assinatura])
    if c.credito_conta_terceiro is False:
        itens.append("crédito em conta de titularidade do autor com movimentação posterior")
    return itens


def _fragilidades(caso: CasoFeatures, dados: DadosExtraidos) -> list[str]:
    itens = [f"{NOMES_SUBSIDIOS[k]} não apresentado" for k in caso.subsidios.ausentes()]
    itens += [s.descricao for s in dados.sinais_alerta if s.severidade in ("alta", "media")]
    return itens


def proposta_acordo(caso: CasoFeatures, dados: DadosExtraidos, rec: Recomendacao) -> str:
    valor = rec.valor_sugerido or 0
    linhas = [
        f"PROPOSTA DE COMPOSIÇÃO AMIGÁVEL — Processo nº {caso.numero}",
        f"À(Ao) {_tratamento(dados)}, patrono(a) de {_autor(dados)}.",
        "",
        "O Banco UFMG S.A., sem reconhecimento de culpa e com o único propósito de encerrar o litígio, propõe:",
        (f"1. Pagamento de {brl(valor)}, em parcela única, no prazo de 15 dias úteis contados da homologação, "
         "por depósito em conta indicada pela parte autora;"),
        ("2. Cancelamento do contrato impugnado, com baixa do saldo devedor e cessação definitiva dos descontos "
         "no benefício previdenciário, no prazo de 5 dias úteis;"),
        ("3. Quitação ampla, geral e irrevogável quanto a todos os pedidos da inicial (declaratório, repetição de "
         "indébito e danos morais), com renúncia ao direito sobre o qual se funda a ação;"),
        "4. Cada parte arca com os honorários de seus advogados; custas na forma da lei (gratuidade, se deferida).",
        "",
        (f"Validade da proposta: 10 dias. Margem interna de negociação: {brl(rec.valor_min or valor)} a "
         f"{brl(rec.valor_max or valor)} (não divulgar à parte contrária)."),
    ]
    if rec.motivos:
        linhas += ["", "Fundamentos internos da oferta:"] + [f"- {m}" for m in rec.motivos]
    return "\n".join(linhas)


def roteiro_defesa(caso: CasoFeatures, dados: DadosExtraidos, rec: Recomendacao) -> str:
    provas, frag = _provas(caso, dados), _fragilidades(caso, dados)
    linhas = [f"ROTEIRO DE CONTESTAÇÃO — Processo nº {caso.numero} ({caso.uf})", ""]
    if rec.tipo == "defesa":
        linhas.append("Estratégia: defesa integral com pedido de improcedência; acordo só se surgir fato novo.")
    else:
        linhas.append("Estratégia: contestar para preservar o prazo enquanto a proposta de acordo é negociada.")
    linhas += ["", ("Preliminares: impugnação à gratuidade (se houver indício de capacidade); ausência de "
                    "interesse quanto a pedidos já atendidos administrativamente.")]
    linhas += ["", "Mérito — provas do banco:"] + ([f"- {p}" for p in provas] or ["- (nenhum subsídio disponível)"])
    linhas += [("- Regularidade da contratação e efetiva disponibilização do crédito; ausência de dano moral "
                "indenizável; inaplicabilidade da repetição em dobro (art. 42, parágrafo único, CDC) por engano "
                "justificável.")]
    if frag:
        linhas += ["", "Pontos a neutralizar (fragilidades):"] + [f"- {f}" for f in frag]
    if dados.resumo_fatos:
        linhas += ["", "Contexto dos autos:", dados.resumo_fatos]
    linhas += ["", "Pedidos: improcedência total; subsidiariamente, redução do dano moral e afastamento da repetição em dobro."]
    return "\n".join(linhas)


def mensagem_contato(caso: CasoFeatures, dados: DadosExtraidos, rec: Recomendacao) -> str:
    adv = dados.advogado_autor
    saudacao = f"Dr(a). {adv.nome.split()[-1]}" if adv.nome else "Dr(a)."
    if rec.tipo != "acordo":
        return ""
    return (
        f"{saudacao}, bom dia. Represento o Banco UFMG no processo {caso.numero} ({_autor(dados)}). "
        f"Temos autorização para uma composição em {brl(rec.valor_sugerido or 0)}, com cancelamento do contrato e "
        "encerramento dos descontos, mediante quitação geral. Podemos conversar hoje? Se preferir, envio a minuta por e-mail"
        + (f" ({adv.email})" if adv.email else "") + "."
    )


def redigir(caso: CasoFeatures, dados: DadosExtraidos, rec: Recomendacao) -> Minutas:
    return Minutas(
        numero=caso.numero, politica_id=rec.politica_id, origem=ORIGEM,
        proposta_acordo=proposta_acordo(caso, dados, rec) if rec.tipo == "acordo" else "",
        roteiro_defesa=roteiro_defesa(caso, dados, rec),
        mensagem_contato=mensagem_contato(caso, dados, rec),
    )
