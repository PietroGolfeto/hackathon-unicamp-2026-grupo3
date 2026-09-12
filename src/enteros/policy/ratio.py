"""Condenação dado que o banco perde, como fração do valor da causa: média e quantis por UF × sub-assunto."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from enteros import config as cfg
from enteros.util import json_dumps

QUANTIS = (0.2, 0.5, 0.8)
N_MIN = 30


def _resumo(s: pd.Series) -> dict:
    return {"n": int(s.size), "media": float(s.mean()),
            **{f"p{int(q*100)}": float(s.quantile(q)) for q in QUANTIS}}


@dataclass
class RatioCondenacao:
    por_uf_sub: dict[str, dict]
    por_sub: dict[str, dict]
    global_: dict

    @classmethod
    def ajustar(cls, base: pd.DataFrame) -> "RatioCondenacao":
        perdas = base[base["perda"] == 1]
        return cls(
            por_uf_sub={f"{uf}|{sub}": _resumo(g["ratio"]) for (uf, sub), g in perdas.groupby(["uf", "sub_assunto"])},
            por_sub={sub: _resumo(g["ratio"]) for sub, g in perdas.groupby("sub_assunto")},
            global_=_resumo(perdas["ratio"]),
        )

    def para(self, uf: str, sub_assunto: str) -> dict:
        r = self.por_uf_sub.get(f"{uf}|{sub_assunto}")
        if r and r["n"] >= N_MIN:
            return r
        return self.por_sub.get(sub_assunto, self.global_)

    def to_json(self, caminho: Path) -> None:
        caminho.parent.mkdir(parents=True, exist_ok=True)
        caminho.write_text(json_dumps({"por_uf_sub": self.por_uf_sub, "por_sub": self.por_sub, "global": self.global_}),
                           encoding="utf-8")

    @classmethod
    def from_json(cls, caminho: Path) -> "RatioCondenacao":
        d = json.loads(caminho.read_text(encoding="utf-8"))
        return cls(por_uf_sub=d["por_uf_sub"], por_sub=d["por_sub"], global_=d["global"])


__all__ = ["RatioCondenacao", "QUANTIS", "cfg"]
