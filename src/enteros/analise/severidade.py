"""Severidade (condenação ÷ valor da causa dado perda): por que não é constante e por que a mediana por célula engana.

Só leitura. Mostra a estrutura de mistura (procedência total ≈ U(0,80–1,00) em toda UF; parcial varia por UF) e a
estabilidade do p50 em células pequenas — evidência para a decisão 33 e para o slide "onde o banco perde mais".
"""

from __future__ import annotations

from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from enteros import config as cfg  # noqa: E402
from enteros.policy.ratio import K_SHRINK  # noqa: E402

N_BOOT = 200
N_CELULA_PEQUENA = 100
COR_PROC, COR_PARC = "#171717", "#ffae35"


def _perdas(base: pd.DataFrame) -> pd.DataFrame:
    col = "perda_sentenca" if "perda_sentenca" in base.columns else "perda"
    return base[base[col] == 1]


def por_uf(base: pd.DataFrame) -> pd.DataFrame:
    perdas = _perdas(base)
    proc = perdas["resultado_micro"] == cfg.MICRO_PROCEDENCIA
    g = pd.DataFrame({"uf": perdas["uf"], "ratio": perdas["ratio"], "proc": proc.astype(float),
                      "ratio_proc": perdas["ratio"].where(proc), "ratio_parc": perdas["ratio"].where(~proc)})
    t = g.groupby("uf").agg(n=("ratio", "size"), ratio=("ratio", "mean"), p_procedencia=("proc", "mean"),
                            media_procedencia=("ratio_proc", "mean"), media_parcial=("ratio_parc", "mean"))
    return t.sort_values("ratio")


def decomposicao(t: pd.DataFrame) -> dict:
    """Quanto da variação entre UFs vem do nível da parcial e quanto da fatia de procedência total."""
    p_bar, parc_bar = float(t["p_procedencia"].mean()), float(t["media_parcial"].mean())
    mix_igual = p_bar * t["media_procedencia"] + (1 - p_bar) * t["media_parcial"]
    parcial_igual = t["p_procedencia"] * t["media_procedencia"] + (1 - t["p_procedencia"]) * parc_bar
    var = float(t["ratio"].var())
    return {"amplitude": [float(t["ratio"].min()), float(t["ratio"].max())],
            "uf_min": t["ratio"].idxmin(), "uf_max": t["ratio"].idxmax(),
            "sd_entre_ufs": float(t["ratio"].std()),
            "share_var_explicada_pela_parcial": float(mix_igual.var() / var) if var else 0.0,
            "share_var_explicada_pela_mistura": float(parcial_igual.var() / var) if var else 0.0,
            "p_procedencia_nacional": p_bar, "media_parcial_nacional": parc_bar,
            "media_procedencia_nacional": float(t["media_procedencia"].mean()),
            "sd_media_procedencia_entre_ufs": float(t["media_procedencia"].std()),
            "sd_media_parcial_entre_ufs": float(t["media_parcial"].std())}


def estabilidade_p50(base: pd.DataFrame, semente: int = cfg.SEMENTE) -> pd.DataFrame:
    """Bootstrap do p50 por célula UF × sub pequena: empírico × encolhido para o sub-assunto (como no modelo)."""
    perdas = _perdas(base)
    rng = np.random.default_rng(semente)
    linhas = []
    for sub, gs in perdas.groupby("sub_assunto"):
        r_sub = gs["ratio"].to_numpy()
        for uf, g in gs.groupby("uf"):
            r = g["ratio"].to_numpy()
            if len(r) >= N_CELULA_PEQUENA:
                continue
            w = len(r) / (len(r) + K_SHRINK)
            emp, enc = [], []
            for _ in range(N_BOOT):
                amostra = rng.choice(r, len(r))
                p50_emp = float(np.quantile(amostra, .5))
                emp.append(p50_emp)
                enc.append(w * p50_emp + (1 - w) * float(np.quantile(rng.choice(r_sub, len(r_sub)), .5)))
            linhas.append({"uf": uf, "sub_assunto": sub, "n": len(r), "p50": float(np.quantile(r, .5)),
                           "sd_p50_empirico": float(np.std(emp)), "sd_p50_encolhido": float(np.std(enc))})
    return pd.DataFrame(linhas).sort_values("n") if linhas else pd.DataFrame()


def _fig_uf(t: pd.DataFrame, out: Path) -> None:
    fig, ax = plt.subplots(figsize=(9, 5.5))
    proc = t["p_procedencia"] * t["media_procedencia"]
    parc = (1 - t["p_procedencia"]) * t["media_parcial"]
    ax.barh(t.index, parc, color=COR_PARC, label="parcial procedência (paga ~60% do pedido)")
    ax.barh(t.index, proc, left=parc, color=COR_PROC, label="procedência total (paga ~90% do pedido)")
    for uf, v in t["ratio"].items():
        ax.text(v + 0.01, uf, f"{v:.2f}", va="center", fontsize=8)
    ax.set_xlim(0, 1.0)
    ax.set_xlabel("condenação ÷ valor da causa quando o banco perde (média por UF)")
    ax.set_title("Quando perde, quanto o banco paga: de 60% (MA) a 84% (AM/AP) do pedido")
    ax.legend(loc="lower right", fontsize=8)
    ax.tick_params(axis="y", labelsize=8)
    fig.tight_layout()
    fig.savefig(out / "severidade_uf.png", dpi=150)
    plt.close(fig)


def _fig_distribuicao(base: pd.DataFrame, t: pd.DataFrame, out: Path) -> None:
    perdas = _perdas(base)
    proc = perdas["resultado_micro"] == cfg.MICRO_PROCEDENCIA
    fig, ax = plt.subplots(figsize=(8, 4.2))
    bins = np.linspace(0.2, 1.0, 33)
    ax.hist(perdas.loc[~proc, "ratio"], bins=bins, color=COR_PARC, alpha=.9, label="parcial procedência")
    ax.hist(perdas.loc[proc, "ratio"], bins=bins, color=COR_PROC, alpha=.85, label="procedência total")
    for uf, cor in ((t["ratio"].idxmin(), "#2e7d32"), (t["ratio"].idxmax(), "#c62828")):
        p50 = float(perdas.loc[perdas["uf"] == uf, "ratio"].median())
        ax.axvline(p50, color=cor, ls="--", lw=1.5, label=f"mediana {uf}: {p50:.2f}")
    ax.set_xlabel("condenação ÷ valor da causa")
    ax.set_ylabel("sentenças perdidas")
    ax.set_title("Duas populações de condenação: a mediana de uma célula pequena pula entre elas")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(out / "severidade_distribuicao.png", dpi=150)
    plt.close(fig)


def analisar(base: pd.DataFrame, out: Path) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    t = por_uf(base)
    dec = decomposicao(t)
    est = estabilidade_p50(base)
    _fig_uf(t, out)
    _fig_distribuicao(base, t, out)
    return {"por_uf": t.reset_index().to_dict(orient="records"), "decomposicao": dec,
            "estabilidade_p50": est.to_dict(orient="records"),
            "estabilidade_resumo": ({"n_celulas_pequenas": int(len(est)),
                                     "sd_p50_empirico_medio": float(est["sd_p50_empirico"].mean()),
                                     "sd_p50_encolhido_medio": float(est["sd_p50_encolhido"].mean())} if len(est) else {})}
