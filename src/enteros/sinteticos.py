"""Gera data/exemplos/sinteticos.csv: processos fictícios amostrados dos modelos ajustados.

Nenhuma linha da base da Enter é copiada. Serve para o repositório rodar (loader, engine, backtest, testes)
em um clone limpo sem a planilha original.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from enteros import config as cfg
from enteros.data.load import carregar_base
from enteros.policy.model import ModeloPerda, SegmentTable
from enteros.policy.ratio import RatioCondenacao

MICROS_PERDA = (cfg.MICRO_PARCIAL, cfg.MICRO_PROCEDENCIA, cfg.MICRO_ACORDO)
MICROS_EXITO = (cfg.MICRO_IMPROCEDENCIA, cfg.MICRO_EXTINCAO)


def gerar(n: int, base: pd.DataFrame, seg: SegmentTable, mod: ModeloPerda, ratio: RatioCondenacao, semente: int) -> pd.DataFrame:
    rng = np.random.default_rng(semente)
    ufs = rng.choice(cfg.UFS, n)
    subs = rng.choice(cfg.SUB_ASSUNTOS, n, p=[(base["sub_assunto"] == s).mean() for s in cfg.SUB_ASSUNTOS])
    docs = {d: rng.binomial(1, base[d].mean(), n) for d in cfg.DOCS}
    vc = np.clip(rng.normal(base["valor_causa"].mean(), base["valor_causa"].std(), n), 1000, 31000).round(2)
    linhas = []
    for i in range(n):
        flags = {d: int(docs[d][i]) for d in cfg.DOCS}
        p, _ = seg.p_perda(subs[i], flags, ufs[i])
        perdeu = rng.random() < p
        r = ratio.para(ufs[i], subs[i])
        if perdeu:
            frac = float(np.clip(rng.normal(r["media"], 0.19), 0.2, 1.0))
            micro = rng.choice(MICROS_PERDA, p=[0.67, 0.315, 0.015])
            if micro == cfg.MICRO_ACORDO:
                frac = float(rng.uniform(0.2, 0.4))
            cond = round(frac * vc[i], 2)
        else:
            micro = rng.choice(MICROS_EXITO, p=[0.67, 0.33])
            cond = 0.0
        tj = next(k for k, v in cfg.TJ_UF.items() if v == ufs[i])
        numero = f"{rng.integers(1_000_000, 9_999_999):07d}-{rng.integers(10, 99):02d}.2025.8.{tj}.{rng.integers(1, 9999):04d}"
        linhas.append({"Número do processo": numero, "UF": ufs[i], "Assunto": "Não reconhece operação",
                       "Sub-assunto": subs[i], "Resultado macro": cfg.NAO_EXITO if perdeu else cfg.EXITO,
                       "Resultado micro": micro, "Valor da causa": vc[i], "Valor da condenação/indenização": cond,
                       **{orig: flags[can] for orig, can in cfg.COLUNAS_SUBSIDIOS.items() if can in cfg.DOCS}})
    return pd.DataFrame(linhas)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", type=Path, default=cfg.ARQ_RAW_XLSX)
    ap.add_argument("--n", type=int, default=3000)
    ap.add_argument("--out", type=Path, default=cfg.ARQ_SINTETICOS)
    args = ap.parse_args()
    base = carregar_base(args.raw)
    df = gerar(args.n, base, SegmentTable.from_json(cfg.ARQ_SEGMENTOS), ModeloPerda.from_json(cfg.ARQ_MODELO_PERDA),
               RatioCondenacao.from_json(cfg.ARQ_RATIO), cfg.SEMENTE)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.out, index=False)
    print(f"{len(df)} processos sintéticos → {args.out}; perda {(df['Resultado macro']==cfg.NAO_EXITO).mean():.3f}")


if __name__ == "__main__":
    main()
