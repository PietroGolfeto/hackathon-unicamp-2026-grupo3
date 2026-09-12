"""Modelos de probabilidade de perda e de condenação, ajustados na base e exportados em JSON legível.

Dois estimadores complementares:
- SegmentTable: P(perda) por segmento (sub × 4 docs preditivos × UF) com shrinkage para o segmento pai
  (sub × 4 docs). É a política em forma de tabela: 100% explicável, sem dependência de modelo.
- ModeloPerda: regressão logística (docs + sub + UF) — suaviza segmentos raros, dá contribuições por feature
  (coef × valor) e é calibrada por construção nesta base (ver reliability em docs/backtest).
"""

from __future__ import annotations

import argparse
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, roc_auc_score
from sklearn.model_selection import StratifiedKFold

from enteros import config as cfg
from enteros.data.load import carregar_base
from enteros.util import json_dumps

log = logging.getLogger(__name__)

CHAVE_PAI = ["sub_assunto", *cfg.DOCS_PREDITIVOS]
CHAVE_SEGMENTO = [*CHAVE_PAI, "uf"]
K_SHRINK = 20.0  # peso do pai em pseudo-observações


def _chave(valores: list) -> str:
    return "|".join(str(v) for v in valores)


@dataclass
class SegmentTable:
    pai: dict[str, dict]  # chave pai -> {n, p}
    seg: dict[str, dict]  # chave segmento -> {n, p_bruto, p}
    p_global: float

    @classmethod
    def ajustar(cls, base: pd.DataFrame) -> "SegmentTable":
        p_global = float(base["perda"].mean())
        pai = base.groupby(CHAVE_PAI)["perda"].agg(["size", "mean"])
        pai_d = {_chave(list(k)): {"n": int(n), "p": float(p)} for k, (n, p) in pai.iterrows()}
        seg = base.groupby(CHAVE_SEGMENTO)["perda"].agg(["size", "mean"])
        seg_d: dict[str, dict] = {}
        for k, (n, p) in seg.iterrows():
            kp = _chave(list(k[:-1]))
            p_pai = pai_d.get(kp, {"p": p_global})["p"]
            p_shr = (n * p + K_SHRINK * p_pai) / (n + K_SHRINK)
            seg_d[_chave(list(k))] = {"n": int(n), "p_bruto": float(p), "p": float(p_shr)}
        return cls(pai=pai_d, seg=seg_d, p_global=p_global)

    def p_perda(self, sub_assunto: str, flags: dict[str, int], uf: str) -> tuple[float, int]:
        """Devolve (p_perda, n do segmento). Cai para o pai e depois para o global se o segmento não existir."""
        chave_pai = _chave([sub_assunto, *[flags[d] for d in cfg.DOCS_PREDITIVOS]])
        s = self.seg.get(f"{chave_pai}|{uf}")
        if s:
            return s["p"], s["n"]
        p = self.pai.get(chave_pai)
        if p:
            return p["p"], p["n"]
        return self.p_global, 0

    def to_json(self, caminho: Path) -> None:
        caminho.parent.mkdir(parents=True, exist_ok=True)
        caminho.write_text(json_dumps({"chave_pai": CHAVE_PAI, "chave_segmento": CHAVE_SEGMENTO, "k_shrink": K_SHRINK,
                                       "p_global": self.p_global, "pai": self.pai, "seg": self.seg}), encoding="utf-8")

    @classmethod
    def from_json(cls, caminho: Path) -> "SegmentTable":
        d = json.loads(caminho.read_text(encoding="utf-8"))
        return cls(pai=d["pai"], seg=d["seg"], p_global=d["p_global"])


def _matriz(base: pd.DataFrame, colunas: list[str] | None = None) -> tuple[pd.DataFrame, list[str]]:
    x = pd.DataFrame({d: base[d].astype(float) for d in cfg.DOCS})
    x["sub_golpe"] = (base["sub_assunto"] == cfg.SUB_GOLPE).astype(float)
    for uf in cfg.UFS[1:]:  # primeira UF (AC) é a referência
        x[f"uf_{uf}"] = (base["uf"] == uf).astype(float)
    if colunas is not None:
        x = x.reindex(columns=colunas, fill_value=0.0)
    return x, list(x.columns)


@dataclass
class ModeloPerda:
    colunas: list[str]
    coef: list[float]
    intercepto: float
    metricas: dict = field(default_factory=dict)
    calibracao: list[dict] = field(default_factory=list)
    versao: str = ""
    medias: dict[str, float] = field(default_factory=dict)  # média de cada coluna na base (referência das contribuições)

    @classmethod
    def ajustar(cls, base: pd.DataFrame, versao: str) -> "ModeloPerda":
        x, colunas = _matriz(base)
        y = base["perda"].to_numpy()
        # métricas honestas: out-of-fold em 5 folds
        oof = np.zeros(len(y))
        for tr, te in StratifiedKFold(5, shuffle=True, random_state=cfg.SEMENTE).split(x, y):
            m = LogisticRegression(max_iter=2000, C=10.0).fit(x.iloc[tr], y[tr])
            oof[te] = m.predict_proba(x.iloc[te])[:, 1]
        bins = pd.cut(oof, np.linspace(0, 1, 11), include_lowest=True)
        cal = (pd.DataFrame({"p": oof, "y": y, "b": bins}).groupby("b", observed=True)
               .agg(n=("y", "size"), p_prevista=("p", "mean"), taxa_real=("y", "mean")))
        ece = float((cal["n"] / cal["n"].sum() * (cal["p_prevista"] - cal["taxa_real"]).abs()).sum())
        metricas = {
            "auc_oof": float(roc_auc_score(y, oof)),
            "brier_oof": float(brier_score_loss(y, oof)),
            "acuracia_oof_0.5": float(((oof > 0.5) == y).mean()),
            "ece_oof": ece,
            "n_treino": int(len(y)),
            "taxa_perda_base": float(y.mean()),
        }
        calib = [{"p_min": float(b.left), "p_max": float(b.right), "n": int(r.n),
                  "p_prevista": float(r.p_prevista), "taxa_real": float(r.taxa_real)} for b, r in cal.iterrows()]
        final = LogisticRegression(max_iter=2000, C=10.0).fit(x, y)
        return cls(colunas=colunas, coef=[float(c) for c in final.coef_[0]], intercepto=float(final.intercept_[0]),
                   metricas=metricas, calibracao=calib, versao=versao,
                   medias={c: float(v) for c, v in x.mean().items()})

    def _linha(self, sub_assunto: str, flags: dict[str, int], uf: str) -> dict[str, float]:
        linha = {d: float(flags[d]) for d in cfg.DOCS}
        linha["sub_golpe"] = float(sub_assunto == cfg.SUB_GOLPE)
        for c in self.colunas:
            if c.startswith("uf_"):
                linha[c] = float(c == f"uf_{uf}")
        return linha

    def p_perda(self, sub_assunto: str, flags: dict[str, int], uf: str) -> float:
        linha = self._linha(sub_assunto, flags, uf)
        z = self.intercepto + sum(c * linha[col] for col, c in zip(self.colunas, self.coef))
        return float(1 / (1 + np.exp(-z)))

    def contribuicoes(self, sub_assunto: str, flags: dict[str, int], uf: str, top: int = 5) -> list[dict]:
        """coef × (valor − média da base), em log-odds de PERDA. Positivo = aumenta o risco do banco em relação
        ao caso médio; negativo = protege. Documento ausente aparece como risco, presente como proteção."""
        linha = self._linha(sub_assunto, flags, uf)
        itens = []
        for col, c in zip(self.colunas, self.coef):
            contrib = c * (linha[col] - self.medias.get(col, 0.0))
            if col in cfg.DOCS:
                nome, valor = cfg.NOME_DOC[col], ("presente" if flags[col] else "ausente")
            elif col == "sub_golpe":
                nome, valor = "Sub-assunto", sub_assunto
            else:
                if linha[col] == 0.0:
                    continue  # só a UF do caso interessa
                nome, valor = "UF", uf
            if abs(contrib) > 1e-9:
                itens.append({"feature": nome, "valor": valor, "contribuicao": round(float(contrib), 3)})
        itens.sort(key=lambda i: -abs(i["contribuicao"]))
        return itens[:top]

    def p_perda_lote(self, base: pd.DataFrame) -> np.ndarray:
        x, _ = _matriz(base, self.colunas)
        z = self.intercepto + x.to_numpy() @ np.array(self.coef)
        return 1 / (1 + np.exp(-z))

    def to_json(self, caminho: Path) -> None:
        caminho.parent.mkdir(parents=True, exist_ok=True)
        caminho.write_text(json_dumps(self.__dict__), encoding="utf-8")

    @classmethod
    def from_json(cls, caminho: Path) -> "ModeloPerda":
        return cls(**json.loads(caminho.read_text(encoding="utf-8")))


def treinar(base: pd.DataFrame, versao: str) -> tuple[SegmentTable, ModeloPerda]:
    seg = SegmentTable.ajustar(base)
    mod = ModeloPerda.ajustar(base, versao)
    return seg, mod


def main() -> None:
    from enteros.policy.ratio import RatioCondenacao

    ap = argparse.ArgumentParser(description="ajusta e exporta os modelos em models/")
    ap.add_argument("--raw", type=Path, default=cfg.ARQ_RAW_XLSX)
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    base = carregar_base(args.raw)
    versao = f"logit-{len(base)}-{pd.Timestamp.today():%Y%m%d}"
    seg, mod = treinar(base, versao)
    seg.to_json(cfg.ARQ_SEGMENTOS)
    mod.to_json(cfg.ARQ_MODELO_PERDA)
    RatioCondenacao.ajustar(base).to_json(cfg.ARQ_RATIO)
    print(json.dumps(mod.metricas, indent=1))
    print(pd.DataFrame(mod.calibracao).round(3).to_string(index=False))
    print(f"segmentos: {len(seg.seg)}  pais: {len(seg.pai)}  → {cfg.DIR_MODELS}")


if __name__ == "__main__":
    main()
