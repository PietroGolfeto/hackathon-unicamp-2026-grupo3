"""Condenação dado que o banco perde em sentença, como fração do valor da causa: média, quantis e razão de
procedência por UF × sub-assunto.

Acordos históricos ficam fora (não são condenações). Células pequenas encolhem para o nível do sub-assunto
(peso n/(n+k)); os quantis de uma mesma célula são monotônicos por construção e continuam após a combinação.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from enteros import config as cfg
from enteros.util import json_dumps

QUANTIS = (0.2, 0.5, 0.8)
N_MIN = 30  # abaixo disso a célula quase não pesa na combinação
K_SHRINK = 30.0  # pseudo-observações do sub-assunto na combinação
CHAVES_NUMERICAS = ("media", *[f"p{int(q * 100)}" for q in QUANTIS], "p_procedencia", "media_parcial", "media_procedencia")


def _resumo(g: pd.DataFrame) -> dict:
    r = g["ratio"]
    micro = g["resultado_micro"]
    parcial = r[micro == cfg.MICRO_PARCIAL]
    proc = r[micro == cfg.MICRO_PROCEDENCIA]
    return {
        "n": int(r.size),
        "media": float(r.mean()),
        **{f"p{int(q * 100)}": float(r.quantile(q)) for q in QUANTIS},
        "p_procedencia": float((micro == cfg.MICRO_PROCEDENCIA).mean()),
        "media_parcial": float(parcial.mean()) if parcial.size else float(r.mean()),
        "media_procedencia": float(proc.mean()) if proc.size else float(r.mean()),
    }


def _encolher(celula: dict, pai: dict, k: float = K_SHRINK) -> dict:
    w = celula["n"] / (celula["n"] + k)
    out = {"n": celula["n"], "peso_proprio": float(w), "n_pai": pai["n"]}
    out.update({c: float(w * celula[c] + (1 - w) * pai[c]) for c in CHAVES_NUMERICAS})
    return out


def _sentencas_perdidas(base: pd.DataFrame) -> pd.DataFrame:
    if "perda_sentenca" in base.columns:
        return base[base["perda_sentenca"] == 1]
    return base[(base["perda"] == 1) & (base["resultado_micro"] != cfg.MICRO_ACORDO)]


@dataclass
class RatioCondenacao:
    por_uf_sub: dict[str, dict]
    por_sub: dict[str, dict]
    global_: dict

    @classmethod
    def ajustar(cls, base: pd.DataFrame) -> "RatioCondenacao":
        perdas = _sentencas_perdidas(base)
        por_sub = {sub: _resumo(g) for sub, g in perdas.groupby("sub_assunto")}
        glob = _resumo(perdas)
        por_uf_sub = {
            f"{uf}|{sub}": _encolher(_resumo(g), por_sub.get(sub, glob))
            for (uf, sub), g in perdas.groupby(["uf", "sub_assunto"])
        }
        return cls(por_uf_sub=por_uf_sub, por_sub=por_sub, global_=glob)

    def para(self, uf: str, sub_assunto: str) -> dict:
        """Célula UF × sub já combinada com o sub-assunto; sem célula, o sub-assunto; sem sub, o global."""
        r = self.por_uf_sub.get(f"{uf}|{sub_assunto}")
        if r:
            return r
        return self.por_sub.get(sub_assunto, self.global_)

    def to_json(self, caminho: Path) -> None:
        caminho.parent.mkdir(parents=True, exist_ok=True)
        caminho.write_text(json_dumps({"por_uf_sub": self.por_uf_sub, "por_sub": self.por_sub, "global": self.global_,
                                       "k_shrink": K_SHRINK, "quantis": QUANTIS}), encoding="utf-8")

    @classmethod
    def from_json(cls, caminho: Path) -> "RatioCondenacao":
        d = json.loads(caminho.read_text(encoding="utf-8"))
        return cls(por_uf_sub=d["por_uf_sub"], por_sub=d["por_sub"], global_=d["global"])


__all__ = ["RatioCondenacao", "QUANTIS", "N_MIN", "K_SHRINK"]
