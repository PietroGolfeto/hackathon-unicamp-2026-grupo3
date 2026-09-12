"""Simula uma política sobre o histórico com resultados reais. ~60k linhas em dezenas de ms."""

from __future__ import annotations

from time import perf_counter
from typing import Any

import numpy as np
import pandas as pd
from core.colunas import FLAGS_SUBSIDIOS
from core.politica import PoliticaParams, custos_reais


def _grupo(d: pd.DataFrame, r: dict[str, np.ndarray], chave: str) -> list[dict[str, Any]]:
    g = pd.DataFrame({
        chave: d[chave].values, "acordo": r["acordo"], "politica": r["custo_politica"],
        "defender": r["custo_defesa_real"], "acordar": r["custo_acordo_real"],
    })
    agg = g.groupby(chave, dropna=False).agg(
        n=("acordo", "size"), pct_acordo=("acordo", "mean"), politica=("politica", "sum"),
        defender_tudo=("defender", "sum"), acordar_tudo=("acordar", "sum"),
    )
    agg["economia_vs_defender"] = agg["defender_tudo"] - agg["politica"]
    agg = agg.reset_index().sort_values(chave)
    return [
        {k: (v.item() if hasattr(v, "item") else v) for k, v in linha.items()}
        for linha in agg.to_dict(orient="records")
    ]


def simular(hist: pd.DataFrame, prm: PoliticaParams) -> dict[str, Any]:
    t0 = perf_counter()
    d = hist if prm.incluir_extincao_no_backtest else hist[hist["resultado_micro"] != "Extinção"]
    d = d.dropna(subset=["p_exito_oof", "valor_causa", "resultado_macro"])
    r = custos_reais(
        d["p_exito_oof"].values, d["condenacao_p20_oof"].values, d["condenacao_p50_oof"].values,
        d["condenacao_p80_oof"].values, d["valor_causa"].values,
        perdeu=(d["resultado_macro"].values == 0), valor_condenacao=d["valor_condenacao"].values,
        prm=prm,
    )
    n = len(d)
    politica = float(r["custo_politica"].sum())
    defender = float(r["custo_defesa_real"].sum())
    acordar = float(r["custo_acordo_real"].sum())
    acordo = r["acordo"]
    if "n_docs" not in d.columns:
        d = d.assign(n_docs=d[list(FLAGS_SUBSIDIOS)].astype(int).sum(axis=1))
    regras, contagens = np.unique(r["regra"], return_counts=True)
    return {
        "n": n,
        "totais": {"politica": politica, "defender_tudo": defender, "acordar_tudo": acordar},
        "economia_vs_defender": {"valor": defender - politica,
                                 "pct": (defender - politica) / defender if defender else 0.0},
        "economia_vs_acordar": {"valor": acordar - politica,
                                "pct": (acordar - politica) / acordar if acordar else 0.0},
        "pct_acordo": float(acordo.mean()) if n else 0.0,
        "n_acordo": int(acordo.sum()),
        "oferta_media": float(r["oferta"][acordo].mean()) if acordo.any() else None,
        "custo_medio_por_processo": politica / n if n else 0.0,
        "por_regra": {str(k): int(v) for k, v in zip(regras, contagens, strict=True)},
        "por_uf": _grupo(d, r, "uf"),
        "por_n_docs": _grupo(d, r, "n_docs"),
        "hipoteses": {"taxa_aceite_esperada": prm.taxa_aceite_esperada},
        "incluir_extincao": prm.incluir_extincao_no_backtest,
        "scores_origem": str(d["scores_origem"].iloc[0]) if n and "scores_origem" in d else None,
        "tempo_ms": round((perf_counter() - t0) * 1000, 1),
    }
