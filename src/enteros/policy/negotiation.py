"""Escada de negociação: curva de aceite (premissa declarada), oferta que minimiza o custo esperado,
piso/teto e decomposição em cancelamento + devolução + dano moral.

`saldo` é o saldo devedor baixado no acordo (receita que o banco deixa de receber): entra no ramo "aceitou"
e, por coerência, no teto — o walk-away é sobre o desembolso total, não só sobre a indenização.
"""

from __future__ import annotations

import numpy as np

from enteros.policy import custos as cst
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


def escada(caso: CaseFeatures, ev_defesa: float, oferta: Oferta, custos: Custos, saldo: float = 0.0) -> Escada:
    """alvo = argmin_S p(S)·(S + saldo + op) + (1 − p(S))·(EV_defesa + op); teto = EV_defesa·(1 − margem) − saldo."""
    vc = caso.valor_causa
    piso = max(oferta.piso_pct_causa * vc, devolucao_simples(caso))
    teto = min(ev_defesa * (1 - oferta.margem_teto) - saldo, oferta.teto_pct_causa * vc)
    teto = max(teto, piso)  # se o EV é menor que o piso, a escada colapsa no piso (o engine não recomendará acordo)
    grade = np.arange(oferta.piso_pct_causa, oferta.teto_pct_causa + 1e-9, oferta.grade_passo)
    valores = grade * vc
    valores = valores[(valores >= piso - 1e-6) & (valores <= teto + 1e-6)]
    if valores.size == 0:
        valores = np.array([piso])
    p = p_aceite(valores / vc, oferta)
    custo = cst.ev_acordo(valores, p, ev_defesa, custos, saldo)
    alvo = float(valores[int(np.argmin(custo))])
    abertura = max(piso, alvo * (1 - oferta.desconto_abertura))
    r = oferta.arredondamento
    return Escada(
        abertura=_arredondar(abertura, r), alvo=_arredondar(alvo, r), teto=_arredondar(teto, r),
        piso=_arredondar(piso, r), p_aceite_alvo=float(p_aceite(alvo / vc, oferta)),
    )


def ev_acordo(esc: Escada, ev_defesa: float, custos: Custos, saldo: float = 0.0) -> float:
    """Custo esperado de propor o alvo: aceitou → paga alvo (+ saldo baixado); recusou → litiga. Operacional sempre."""
    return float(cst.ev_acordo(esc.alvo, esc.p_aceite_alvo, ev_defesa, custos, saldo))


def decompor(caso: CaseFeatures, alvo: float) -> Decomposicao:
    dev = devolucao_simples(caso)
    return Decomposicao(devolucao_parcelas=round(dev, 2), saldo_baixado=round(float(caso.saldo_devedor or 0.0), 2),
                        dano_moral=round(max(alvo - dev, 0.0), 2))


def escada_lote(ev_defesa: np.ndarray, valor_causa: np.ndarray, oferta: Oferta, custos: Custos,
                saldo: np.ndarray | float = 0.0, s50: float | None = None) -> tuple[np.ndarray, np.ndarray]:
    """Versão vetorizada do alvo da escada para o backtest: (alvo, p_aceite_alvo) por linha.
    `s50` sobrescreve a âncora da curva de aceite (sensibilidade)."""
    o = oferta if s50 is None else oferta.model_copy(update={"aceite_s50": s50})
    grade = np.arange(o.piso_pct_causa, o.teto_pct_causa + 1e-9, o.grade_passo)
    pa = p_aceite(grade, o)  # (G,)
    vc = np.asarray(valor_causa, dtype=float)[:, None]
    ofertas = grade[None, :] * vc  # (N, G)
    ev = np.asarray(ev_defesa, dtype=float)[:, None]
    sal = np.asarray(saldo, dtype=float).reshape(-1, 1) if np.ndim(saldo) else float(saldo)
    teto = np.minimum(ev * (1 - o.margem_teto) - sal, o.teto_pct_causa * vc)
    piso = o.piso_pct_causa * vc
    custo = cst.ev_acordo(ofertas, pa[None, :], ev, custos, sal)
    custo = np.where((ofertas <= teto + 1e-9) & (ofertas >= piso - 1e-9), custo, np.inf)
    idx = np.argmin(custo, axis=1)
    linhas = np.arange(len(idx))
    alvo = np.where(np.isfinite(custo[linhas, idx]), ofertas[linhas, idx], piso[:, 0])
    return alvo, np.asarray(p_aceite(alvo / vc[:, 0], o), dtype=float)
