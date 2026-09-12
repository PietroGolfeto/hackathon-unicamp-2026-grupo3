"""Compara variantes do modelo de P(perda) pela métrica que importa para a política: o custo de decisão
out-of-fold em R$ (mesmos folds, mesmos custos, mesma regra de EV com oferta fixa — só `p` muda).

Saída: docs/modelo/comparacao.{json,md}. É a evidência da decisão 31: a logística aditiva já está no teto;
interações, saturação, valor da causa, árvores e tabelas de células não compram nada.
"""

from __future__ import annotations

import argparse
import logging
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier

from enteros import config as cfg
from enteros.data.load import carregar_base
from enteros.policy import custos
from enteros.policy.model import (
    COL_SUB,
    PREFIXO_UF,
    SegmentTable,
    UF_REFERENCIA,
    _matriz,
    folds_padrao,
    metricas_de,
    prever_oof,
)
from enteros.policy.params import Politica, carregar_politica
from enteros.util import json_dumps

log = logging.getLogger(__name__)

ESCALA_UF_ENCOLHIDA = 0.3
HGB_PARAMS = {"max_iter": 300, "learning_rate": 0.05, "max_depth": 4, "random_state": 0}
N_MIN_CELULA = 1


def _desenho(base: pd.DataFrame, docs: tuple[str, ...], uf: bool = True, vc: bool = False, interacoes: bool = False,
             saturado: bool = False) -> pd.DataFrame:
    x_full, _ = _matriz(base)
    cols = [*docs, COL_SUB]
    x = x_full[cols].copy()
    if interacoes:
        pred = list(cfg.DOCS_PREDITIVOS)
        for i, a in enumerate(pred):
            for b in pred[i + 1:]:
                x[f"{a}*{b}"] = x[a] * x[b]
            x[f"{COL_SUB}*{a}"] = x[COL_SUB] * x[a]
    if saturado:
        padrao = base["sub_assunto"].astype(str) + "|" + base[list(cfg.DOCS_PREDITIVOS)].astype(int).astype(str).agg("".join, axis=1)
        for p in sorted(padrao.unique())[1:]:
            x[f"pat_{p}"] = (padrao == p).astype(float)
        x = x.drop(columns=cols)
    if uf:
        for c in x_full.columns:
            if c.startswith(PREFIXO_UF) and c != f"{PREFIXO_UF}{UF_REFERENCIA}":
                x[c] = x_full[c]
    if vc:
        x["vc"] = (base["valor_causa"] - base["valor_causa"].mean()) / base["valor_causa"].std()
    return x


def _oof_tabela(base: pd.DataFrame, folds: list, k_shrink: float | None) -> np.ndarray:
    """Tabela de segmentos (v1) ou células brutas, ajustadas fold a fold."""
    oof = np.zeros(len(base))
    chave = (base["sub_assunto"].astype(str) + "|" + base[list(cfg.DOCS_PREDITIVOS)].astype(int).astype(str).agg("|".join, axis=1)
             + "|" + base["uf"].astype(str))
    for tr, te in folds:
        if k_shrink is None:
            medias = base["perda"].iloc[tr].groupby(chave.iloc[tr]).mean()
            oof[te] = chave.iloc[te].map(medias).fillna(base["perda"].iloc[tr].mean()).to_numpy()
        else:
            st = SegmentTable.ajustar(base.iloc[tr], k_shrink)
            sub = base["sub_assunto"].to_numpy()
            ufs = base["uf"].to_numpy()
            flags = base[list(cfg.DOCS)].astype(int).to_dict(orient="records")
            oof[te] = [st.p_perda(sub[i], flags[i], ufs[i])[0] for i in te]
    return np.clip(oof, 1e-3, 1 - 1e-3)


def _oof_hgb(base: pd.DataFrame, y: np.ndarray, folds: list) -> np.ndarray:
    x = base[list(cfg.DOCS)].astype(int).copy()
    x[COL_SUB] = (base["sub_assunto"] == cfg.SUB_GOLPE).astype(int)
    x["uf"] = pd.Categorical(base["uf"]).codes
    x["vc"] = base["valor_causa"].to_numpy()
    oof = np.zeros(len(y))
    for tr, te in folds:
        m = HistGradientBoostingClassifier(categorical_features=[x.columns.get_loc("uf")], **HGB_PARAMS).fit(x.iloc[tr], y[tr])
        oof[te] = m.predict_proba(x.iloc[te])[:, 1]
    return oof


def comparar(base: pd.DataFrame, politica: Politica | None = None) -> dict:
    politica = politica or carregar_politica()
    treino = base[base["acordo"] == 0].reset_index(drop=True) if "acordo" in base.columns else base.reset_index(drop=True)
    y = treino["perda"].to_numpy()
    x0 = _desenho(treino, cfg.DOCS)
    folds = folds_padrao(x0, y)
    d4 = cfg.DOCS_PREDITIVOS
    variantes: list[tuple[str, callable]] = [
        ("Logística 6 docs + sub + UF (v1)", lambda: prever_oof(_desenho(treino, cfg.DOCS), y, folds)[0]),
        ("Logística 4 docs + sub + UF (v2, escolhida)", lambda: prever_oof(_desenho(treino, d4), y, folds)[0]),
        ("… sem UF", lambda: prever_oof(_desenho(treino, d4, uf=False), y, folds)[0]),
        ("… + valor da causa", lambda: prever_oof(_desenho(treino, d4, vc=True), y, folds)[0]),
        ("… + interações docs×docs e sub×docs", lambda: prever_oof(_desenho(treino, d4, interacoes=True), y, folds)[0]),
        ("… saturada sub×docs (32 células) + UF", lambda: prever_oof(_desenho(treino, d4, saturado=True), y, folds)[0]),
        (f"… UF encolhida (colunas × {ESCALA_UF_ENCOLHIDA})", lambda: prever_oof(_escalar_uf(_desenho(treino, d4)), y, folds)[0]),
        ("HistGradientBoosting (6 docs + sub + UF + VC)", lambda: _oof_hgb(treino, y, folds)),
        ("Tabela de segmentos k=20 (estimador da v1)", lambda: _oof_tabela(treino, folds, 20.0)),
        ("Células brutas UF×sub×4 docs", lambda: _oof_tabela(treino, folds, None)),
    ]
    linhas = []
    cache: dict[str, np.ndarray] = {}
    for nome, fn in variantes:
        t0 = time.perf_counter()
        p = fn()
        cache[nome] = p
        m = metricas_de(p, y)
        custo = custos.custo_regra_fixa(p, treino, politica)
        linhas.append({"modelo": nome, **{k: round(v, 4) for k, v in m.items()}, "custo_oof": custo["custo_total"],
                       "share_acordo": custo["share_acordo"], "tempo_s": round(time.perf_counter() - t0, 1)})
        log.info("%s: AUC %.4f custo R$ %.1fM", nome, m["auc_oof"], custo["custo_total"] / 1e6)
    # engine v1: média entre tabela e logística 6 docs
    p_mix = 0.5 * (cache["Tabela de segmentos k=20 (estimador da v1)"] + cache["Logística 6 docs + sub + UF (v1)"])
    m = metricas_de(p_mix, y)
    custo = custos.custo_regra_fixa(p_mix, treino, politica)
    linhas.append({"modelo": "Engine v1: média(tabela, logística 6 docs)", **{k: round(v, 4) for k, v in m.items()},
                   "custo_oof": custo["custo_total"], "share_acordo": custo["share_acordo"], "tempo_s": 0.0})
    referencia = custos.custo_regra_fixa(np.zeros(len(y)), treino, politica)
    oraculo = custos.custo_regra_fixa(y.astype(float), treino, politica)
    return {
        "n_treino": int(len(y)), "n_acordos_excluidos": int(len(base) - len(treino)), "n_folds": len(folds),
        "cenario": politica.comparacao.model_dump(), "custos": politica.custos.model_dump(),
        "custo_defender_tudo": referencia["custo_defender_tudo"], "custo_oraculo": oraculo["custo_total"],
        "linhas": linhas,
    }


def _escalar_uf(x: pd.DataFrame) -> pd.DataFrame:
    x = x.copy()
    cols = [c for c in x.columns if c.startswith(PREFIXO_UF)]
    x[cols] = x[cols] * ESCALA_UF_ENCOLHIDA  # penalidade L2 efetiva maior nos coeficientes de UF
    return x


def para_markdown(res: dict) -> str:
    brl = lambda v: f"R$ {v/1e6:,.1f}M"  # noqa: E731
    ganho_max = res["custo_defender_tudo"] - res["custo_oraculo"]
    linhas = [
        "# Comparação de modelos de P(perda) pelo custo de decisão out-of-fold",
        "",
        f"Base: {res['n_treino']:,} sentenças ({res['n_acordos_excluidos']} acordos históricos excluídos), {res['n_folds']} folds "
        f"estratificados (semente {cfg.SEMENTE}). Regra comum: acordo quando EV_acordo < EV_defesa com oferta fixa de "
        f"{res['cenario']['oferta_pct_causa']:.0%} do VC e aceite {res['cenario']['taxa_aceite']:.0%}; custos de `policy.yaml`. "
        f"Só a probabilidade muda entre linhas.",
        "",
        f"Defender tudo: **{brl(res['custo_defender_tudo'])}** · Oráculo (resultado conhecido): **{brl(res['custo_oraculo'])}** "
        f"→ ganho máximo possível {brl(ganho_max)}.",
        "",
        "| modelo | AUC | log-loss | Brier | ECE | custo OOF | % acordo | captura do ganho máximo |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for l in res["linhas"]:
        captura = (res["custo_defender_tudo"] - l["custo_oof"]) / ganho_max if ganho_max else 0.0
        linhas.append(f"| {l['modelo']} | {l['auc_oof']:.4f} | {l['logloss_oof']:.4f} | {l['brier_oof']:.4f} | {l['ece_oof']:.4f} | "
                      f"{brl(l['custo_oof'])} | {l['share_acordo']:.1%} | {captura:.1%} |")
    melhor = min(res["linhas"], key=lambda l: l["custo_oof"])
    pior = max(res["linhas"], key=lambda l: l["custo_oof"])
    linhas += [
        "",
        f"Amplitude entre o melhor ({melhor['modelo']}) e o pior ({pior['modelo']}): **{brl(pior['custo_oof'] - melhor['custo_oof'])}** "
        f"({(pior['custo_oof'] - melhor['custo_oof']) / res['custo_defender_tudo']:.1%} do custo de defender tudo). "
        "A escolha do modelo não é onde está o dinheiro; a estrutura de custos, o valor da informação e a oferta são.",
    ]
    return "\n".join(linhas) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description="compara modelos de P(perda) pelo custo de decisão OOF")
    ap.add_argument("--raw", type=Path, default=cfg.ARQ_RAW_XLSX)
    ap.add_argument("--out", type=Path, default=cfg.DIR_MODELO_DOCS)
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    res = comparar(carregar_base(args.raw))
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "comparacao.json").write_text(json_dumps(res, default=float), encoding="utf-8")
    md = para_markdown(res)
    (args.out / "comparacao.md").write_text(md, encoding="utf-8")
    print(md)


if __name__ == "__main__":
    main()
