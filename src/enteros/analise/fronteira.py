"""Fronteira de política: varre os knobs da oferta (âncora da curva de aceite usada no desenho, teto, margem) e das
faixas, e mede a economia sob mundos de aceite diferentes do assumido. Só leitura: o policy.yaml não muda; a saída é a
fronteira "economia esperada × economia no pior mundo" para o gestor escolher quanto risco de aceite quer correr.
Os limiares das faixas quase não movem nada (a regra de custo esperado já decide); o que troca retorno por robustez é
o nível da oferta.
"""

from __future__ import annotations

from itertools import product
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from enteros import config as cfg  # noqa: E402
from enteros.analise.comum import engine_com  # noqa: E402
from enteros.backtest.replay import avaliar  # noqa: E402
from enteros.policy import custos as cst  # noqa: E402
from enteros.policy.engine import Engine  # noqa: E402
from enteros.policy.negotiation import p_aceite  # noqa: E402

GRADE_PADRAO: dict[str, tuple[float, ...]] = {
    "aceite_s50": (0.20, 0.25, 0.30, 0.35, 0.40, 0.50),  # âncora assumida no desenho da escada (define o alvo)
    "teto_pct_causa": (0.40, 0.50, 0.60, 0.70),
    "margem_teto": (0.10, 0.30),
    "limiar_verde": (0.15, 0.30),
}
MUNDOS_S50 = (0.25, 0.30, 0.35, 0.40, 0.50)  # 0,50 é estresse: a 30% do VC quase ninguém aceita
KNOBS = tuple(GRADE_PADRAO)


def custos_por_mundo(df: pd.DataFrame, eng: Engine, mundos: tuple[float, ...]) -> dict[str, float]:
    """Avalia a política de `eng` uma vez e mede o custo realizado sob cada âncora de aceite do mundo."""
    c, o = eng.politica.custos, eng.politica.oferta
    p = df["p_perda_hat"].to_numpy(dtype=float)
    av = avaliar(df, eng, p)
    real_def = df["custo_real_defesa"].to_numpy(dtype=float)
    vc = df["valor_causa"].to_numpy(dtype=float)
    acordo = av["decisao"] == cfg.DECISAO_ACORDO
    out = {"share_acordo": float(acordo.mean()), "custo_defender_tudo": float(real_def.sum())}
    for s in mundos:
        a = np.asarray(p_aceite(av["alvo"] / vc, o.model_copy(update={"aceite_s50": s})), dtype=float)
        custo = np.where(acordo, cst.ev_acordo(av["alvo"], a, real_def, c), real_def)
        out[f"custo_s50_{s:.2f}"] = float(custo.sum())
    return out


def grade(df: pd.DataFrame, eng: Engine, grade: dict[str, tuple[float, ...]] | None = None,
          mundos: tuple[float, ...] = MUNDOS_S50) -> pd.DataFrame:
    grade = grade or GRADE_PADRAO
    s50_assumido = eng.politica.oferta.aceite_s50
    if s50_assumido not in mundos:
        mundos = tuple(sorted({*mundos, s50_assumido}))
    knobs = list(grade)
    linhas = []
    for valores in product(*[grade[k] for k in knobs]):
        cfg_knobs = dict(zip(knobs, valores, strict=True))
        e2 = engine_com(eng, **cfg_knobs)
        r = custos_por_mundo(df, e2, mundos)
        custos_m = {s: r[f"custo_s50_{s:.2f}"] for s in mundos}
        total = r["custo_defender_tudo"]
        base = custos_m[s50_assumido]
        pior = max(custos_m.values())
        linhas.append({**cfg_knobs, "share_acordo": r["share_acordo"], "custo_base": base,
                       "economia_pct_base": 1 - base / total,
                       **{f"economia_pct_s50_{s:.2f}": 1 - c / total for s, c in custos_m.items()},
                       "custo_pior": pior, "economia_pct_pior": 1 - pior / total,
                       "custo_medio": float(np.mean(list(custos_m.values()))),
                       "economia_pct_media": 1 - float(np.mean(list(custos_m.values()))) / total})
    return pd.DataFrame(linhas)


def pareto(t: pd.DataFrame, x: str = "economia_pct_pior", y: str = "economia_pct_base") -> pd.DataFrame:
    """Configurações não dominadas: mais economia no pior mundo sem perder economia no mundo assumido."""
    ordenado = t.sort_values([x, y], ascending=[False, False]).reset_index(drop=True)
    melhor = -np.inf
    manter = []
    for _, linha in ordenado.iterrows():
        if linha[y] > melhor + 1e-9:
            melhor = linha[y]
            manter.append(True)
        else:
            manter.append(False)
    return ordenado[manter].sort_values(x)


def _knobs_atuais(eng: Engine, knobs: tuple[str, ...]) -> dict[str, float]:
    pol = eng.politica
    return {k: getattr(pol.faixas, k) if hasattr(pol.faixas, k) else getattr(pol.oferta, k) for k in knobs}


def linha_atual(t: pd.DataFrame, eng: Engine) -> pd.Series | None:
    m = t
    for k, v in _knobs_atuais(eng, tuple(k for k in KNOBS if k in t.columns)).items():
        m = m[np.isclose(m[k], v)]
    return m.iloc[0] if len(m) else None


def um_de_cada_vez(t: pd.DataFrame, eng: Engine) -> list[dict]:
    """Efeito de mover um knob por vez a partir da política atual."""
    knobs = tuple(k for k in KNOBS if k in t.columns)
    atual = _knobs_atuais(eng, knobs)
    linhas = []
    for knob in knobs:
        m = t
        for k in knobs:
            if k != knob:
                m = m[np.isclose(m[k], atual[k])]
        for _, r in m.sort_values(knob).iterrows():
            linhas.append({"knob": knob, "valor": float(r[knob]), "share_acordo": r["share_acordo"],
                           "economia_pct_base": r["economia_pct_base"], "economia_pct_pior": r["economia_pct_pior"],
                           "economia_pct_media": r["economia_pct_media"], "atual": bool(np.isclose(r[knob], atual[knob]))})
    return linhas


def _fig(t: pd.DataFrame, pf: pd.DataFrame, atual: pd.Series | None, robusta: pd.Series, out: Path) -> None:
    fig, ax = plt.subplots(figsize=(7.5, 4.8))
    sc = ax.scatter(t["economia_pct_pior"] * 100, t["economia_pct_base"] * 100, c=t["aceite_s50"], cmap="viridis", s=22, alpha=.75)
    ax.plot(pf["economia_pct_pior"] * 100, pf["economia_pct_base"] * 100, "-", color="#ffae35", lw=2, label="fronteira: retorno × robustez")
    ax.scatter([robusta["economia_pct_pior"] * 100], [robusta["economia_pct_base"] * 100], marker="D", s=90, color="#2e7d32", zorder=5,
               label=f"mais robusta (oferta ancorada em {robusta['aceite_s50']:.2f}: {robusta['economia_pct_base']:.0%} esperado / {robusta['economia_pct_pior']:.0%} no pior mundo)")
    if atual is not None:
        ax.scatter([atual["economia_pct_pior"] * 100], [atual["economia_pct_base"] * 100], marker="*", s=240, color="#171717", zorder=6,
                   label=f"política atual ({atual['economia_pct_base']:.0%} esperado / {atual['economia_pct_pior']:.0%} no pior mundo)")
    cb = fig.colorbar(sc, ax=ax)
    cb.set_label("âncora da curva de aceite usada para desenhar a oferta (s50)")
    ax.set_xlabel("economia se o mundo aceitar muito menos do que assumimos (pior mundo, %)")
    ax.set_ylabel("economia se o mundo for como assumimos (%)")
    ax.set_title("Quanto oferecer: retorno esperado × robustez ao aceite")
    ax.legend(fontsize=7, loc="lower left")
    fig.tight_layout()
    fig.savefig(out / "fronteira_politica.png", dpi=150)
    plt.close(fig)


def analisar(df: pd.DataFrame, eng: Engine, out: Path, grade_knobs: dict[str, tuple[float, ...]] | None = None,
             mundos: tuple[float, ...] = MUNDOS_S50) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    t = grade(df, eng, grade_knobs, mundos)
    pf = pareto(t)
    atual = linha_atual(t, eng)
    robusta = t.loc[t["economia_pct_pior"].idxmax()]
    _fig(t, pf, atual, robusta, out)
    return {"mundos_s50": list(mundos), "n_configuracoes": int(len(t)), "tabela": t.to_dict(orient="records"),
            "pareto": pf.to_dict(orient="records"), "atual": None if atual is None else atual.to_dict(),
            "robusta": robusta.to_dict(), "um_de_cada_vez": um_de_cada_vez(t, eng),
            "melhor_base": t.loc[t["economia_pct_base"].idxmax()].to_dict(),
            "melhor_media": t.loc[t["economia_pct_media"].idxmax()].to_dict()}
