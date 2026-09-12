"""Scores out-of-fold dos 60 mil processos para o portal (`data/derived/historico_scored.csv`, não versionado).

Colunas exatamente as de `core.modelo.COLUNAS_HISTORICO_SCORED`: o `load-historico` da API anexa `p_exito_oof` e os
quantis de condenação por processo e o backtest do gestor passa a usar probabilidade honesta (cada caso pontuado
por um modelo que não o viu; a severidade por UF × sub também é ajustada sem o fold).
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import numpy as np
import pandas as pd

from enteros import config as cfg
from enteros.data.load import carregar_base
from enteros.policy.model import _matriz, colunas_ajuste, folds_padrao, prever_oof
from enteros.policy.ratio import RatioCondenacao

log = logging.getLogger(__name__)

# nome canônico do engine -> nome do portal (core.caso.Subsidios)
FLAGS_PORTAL = {"contrato": "contrato", "extrato": "extrato", "comprovante": "comprovante_credito", "dossie": "dossie",
                "demonstrativo": "demonstrativo_divida", "laudo": "laudo_referenciado"}
COLUNAS_SCORED = (
    "numero", "uf", "sub_assunto", "resultado_macro", "resultado_micro", "valor_causa", "valor_condenacao",
    *FLAGS_PORTAL.values(), "p_exito_oof", "condenacao_p20_oof", "condenacao_p50_oof", "condenacao_p80_oof", "fold",
)
QUANTIS = ("p20", "p50", "p80")


def _colunas_esperadas() -> tuple[str, ...]:
    try:  # o contrato do portal, quando o workspace está instalado
        from core.modelo import COLUNAS_HISTORICO_SCORED

        return tuple(COLUNAS_HISTORICO_SCORED)
    except ImportError:
        return COLUNAS_SCORED


def pontuar_oof(base: pd.DataFrame) -> pd.DataFrame:
    sent = (base["acordo"] == 0).to_numpy() if "acordo" in base.columns else np.ones(len(base), dtype=bool)
    y = base["perda"].to_numpy()
    x_full, colunas = _matriz(base)
    x = x_full[colunas_ajuste(colunas)]
    p = np.full(len(base), np.nan)
    fold = np.full(len(base), -1)
    quantis = {q: np.full(len(base), np.nan) for q in QUANTIS}
    folds = folds_padrao(x.loc[sent], y[sent])
    idx_sent = np.flatnonzero(sent)
    oof, f = prever_oof(x.loc[sent], y[sent], folds)
    p[idx_sent], fold[idx_sent] = oof, f
    vc = base["valor_causa"].to_numpy(dtype=float)
    for k, (tr, te) in enumerate(folds):
        ratio = RatioCondenacao.ajustar(base.iloc[idx_sent[tr]])
        linhas = idx_sent[te]
        pares = base.iloc[linhas][["uf", "sub_assunto"]].astype(str)
        for q in QUANTIS:
            cache = {}
            vals = np.empty(len(linhas))
            for j, (uf, sub) in enumerate(zip(pares["uf"], pares["sub_assunto"], strict=True)):
                chave = f"{uf}|{sub}"
                if chave not in cache:
                    cache[chave] = ratio.para(uf, sub)[q]
                vals[j] = cache[chave]
            quantis[q][linhas] = vals * vc[linhas]
    # acordos históricos (fora do treino): in-sample, fold -1
    if (~sent).any():
        from enteros.policy.engine import Engine

        eng = Engine.carregar()
        p[~sent] = eng.modelo.p_perda_lote(base.loc[~sent])
        for i in np.flatnonzero(~sent):
            r = eng.ratio.para(str(base["uf"].iat[i]), str(base["sub_assunto"].iat[i]))
            for q in QUANTIS:
                quantis[q][i] = r[q] * vc[i]
    out = pd.DataFrame({
        "numero": base["numero"].astype(str), "uf": base["uf"], "sub_assunto": base["sub_assunto"],
        "resultado_macro": base["resultado_macro"], "resultado_micro": base["resultado_micro"],
        "valor_causa": base["valor_causa"], "valor_condenacao": base["valor_condenacao"],
        **{portal: base[eng_col].astype(int) for eng_col, portal in FLAGS_PORTAL.items()},
        "p_exito_oof": np.clip(1.0 - p, 0.001, 0.999),
        **{f"condenacao_{q}_oof": quantis[q] for q in QUANTIS}, "fold": fold,
    })
    esperadas = _colunas_esperadas()
    if tuple(out.columns) != esperadas:
        raise ValueError(f"colunas fora do contrato do portal: {list(out.columns)} != {list(esperadas)}")
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="scores OOF para o portal")
    ap.add_argument("--raw", type=Path, default=cfg.ARQ_RAW_XLSX)
    ap.add_argument("--out", type=Path, default=cfg.ARQ_SCORED)
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    out = pontuar_oof(carregar_base(args.raw))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.out, index=False)
    print(f"{len(out):,} linhas → {args.out} (colunas: {len(out.columns)}; p_exito_oof médio {out['p_exito_oof'].mean():.3f}; "
          f"folds {sorted(out['fold'].unique())})")


if __name__ == "__main__":
    main()
