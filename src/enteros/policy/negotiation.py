"""Escada de negociação: curva de aceite (premissa declarada), oferta que minimiza o custo esperado,
piso/teto e decomposição em cancelamento + devolução + dano moral."""

from __future__ import annotations

import numpy as np

from enteros.policy.params import Custos, Oferta
from enteros.schemas import CaseFeatures, Decomposicao, Escada


def p_aceite(fracao_causa: np.ndarray | float, oferta: Oferta) -> np.ndarray | float:
    """Probabilidade de o autor aceitar uma oferta igual a `fracao_causa` × valor da causa (logística)."""
    return 1.0 / (1.0 + np.exp(-(np.asarray(fracao_causa, dtype=float) - oferta.aceite_s50) / oferta.aceite_largura))


def _arredondar(v: float, passo: float) -> float:
    return float(np.round(v / passo) * passo)


def devolucao_simples(caso: CaseFeatures) -> float:
    if caso.parcelas_pagas and caso.valor_parcela:
        return float(caso.parcelas_pagas * caso.valor_parcela)
    return 0.0


def escada(caso: CaseFeatures, ev_defesa: float, oferta: Oferta, custos: Custos) -> Escada:
    """alvo = argmin_S p(S)·(S + op) + (1 − p(S))·(EV_defesa + op); teto = EV_defesa·(1 − margem)."""
    vc = caso.valor_causa
    piso = max(oferta.piso_pct_causa * vc, devolucao_simples(caso))
    teto = min(ev_defesa * (1 - oferta.margem_teto), oferta.teto_pct_causa * vc)
    teto = max(teto, piso)  # se o EV é menor que o piso, a escada colapsa no piso (o engine não recomendará acordo)
    grade = np.arange(oferta.piso_pct_causa, oferta.teto_pct_causa + 1e-9, oferta.grade_passo)
    valores = grade * vc
    valores = valores[(valores >= piso - 1e-6) & (valores <= teto + 1e-6)]
    if valores.size == 0:
        valores = np.array([piso])
    p = p_aceite(valores / vc, oferta)
    custo = p * (valores + custos.custo_escritorio_acordo) + (1 - p) * (ev_defesa + custos.custo_escritorio_acordo)
    alvo = float(valores[int(np.argmin(custo))])
    abertura = max(piso, alvo * (1 - oferta.desconto_abertura))
    r = oferta.arredondamento
    return Escada(
        abertura=_arredondar(abertura, r), alvo=_arredondar(alvo, r), teto=_arredondar(teto, r),
        piso=_arredondar(piso, r), p_aceite_alvo=float(p_aceite(alvo / vc, oferta)),
    )


def ev_acordo(esc: Escada, ev_defesa: float, custos: Custos) -> float:
    """Custo esperado de propor o alvo: aceitou → paga alvo; recusou → litiga (EV_defesa). Custo operacional sempre."""
    a = esc.p_aceite_alvo
    return float(a * esc.alvo + (1 - a) * ev_defesa + custos.custo_escritorio_acordo)


def decompor(caso: CaseFeatures, alvo: float) -> Decomposicao:
    dev = devolucao_simples(caso)
    return Decomposicao(devolucao_parcelas=round(dev, 2), saldo_baixado=round(float(caso.saldo_devedor or 0.0), 2),
                        dano_moral=round(max(alvo - dev, 0.0), 2))
