"""Utilitários compartilhados pelas análises: engine com parâmetros alternativos e custo realizado sob outro mundo."""

from __future__ import annotations

from dataclasses import replace

import numpy as np
import pandas as pd

from enteros import config as cfg
from enteros.backtest.replay import avaliar
from enteros.policy import custos as cst
from enteros.policy.engine import Engine
from enteros.policy.negotiation import p_aceite

CHAVES_FAIXAS = ("limiar_verde", "limiar_vermelha", "evsi_min_pct_causa")
CHAVES_OFERTA = ("margem_teto", "aceite_s50", "aceite_largura", "teto_pct_causa", "piso_pct_causa")


def engine_com(eng: Engine, **knobs: float) -> Engine:
    """Cópia do engine com parâmetros de faixas/oferta alterados (em memória; o policy.yaml não muda)."""
    pol = eng.politica
    faixas = pol.faixas.model_copy(update={k: v for k, v in knobs.items() if k in CHAVES_FAIXAS})
    oferta = pol.oferta.model_copy(update={k: v for k, v in knobs.items() if k in CHAVES_OFERTA})
    desconhecidas = set(knobs) - set(CHAVES_FAIXAS) - set(CHAVES_OFERTA)
    if desconhecidas:
        raise KeyError(f"knobs desconhecidos: {sorted(desconhecidas)}")
    return replace(eng, politica=pol.model_copy(update={"faixas": faixas, "oferta": oferta}))


def custo_realizado(df: pd.DataFrame, eng_desenho: Engine, s50_mundo: float | None = None,
                    largura_mundo: float | None = None) -> dict[str, float]:
    """Política desenhada com a curva de aceite de `eng_desenho`, mas o mundo aceita segundo (s50_mundo, largura_mundo).

    Custo realizado = em acordo: a_mundo·alvo + (1 − a_mundo)·custo real de defender + operacional; em defesa: custo real.
    """
    c, o = eng_desenho.politica.custos, eng_desenho.politica.oferta
    p = df["p_perda_hat"].to_numpy(dtype=float)
    av = avaliar(df, eng_desenho, p)
    real_def = df["custo_real_defesa"].to_numpy(dtype=float)
    mundo = o.model_copy(update={k: v for k, v in (("aceite_s50", s50_mundo), ("aceite_largura", largura_mundo)) if v is not None})
    a = np.asarray(p_aceite(av["alvo"] / df["valor_causa"].to_numpy(dtype=float), mundo), dtype=float)
    acordo = av["decisao"] == cfg.DECISAO_ACORDO
    custo = np.where(acordo, cst.ev_acordo(av["alvo"], a, real_def, c), real_def)
    total_def = float(real_def.sum())
    return {"custo": float(custo.sum()), "economia_pct": 1 - float(custo.sum()) / total_def,
            "share_acordo": float(acordo.mean()), "aceite_medio": float(a[acordo].mean()) if acordo.any() else 0.0,
            "custo_defender_tudo": total_def}


def brl(v: float) -> str:
    return f"R$ {v / 1e6:,.1f}M" if abs(v) >= 1e6 else f"R$ {v:,.0f}"
