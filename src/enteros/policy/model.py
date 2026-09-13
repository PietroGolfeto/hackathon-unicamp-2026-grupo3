"""Modelo de probabilidade de perda e tabela de segmentos, ajustados na base e exportados em JSON legível.

ModeloPerda — regressão logística aditiva em contrato, extrato, comprovante, demonstrativo, sub-assunto e UF:
- dossiê e laudo ficam nas colunas exportadas com coeficiente 0 (efeito nulo na base; teste LR conjunto p=0,26);
- UF é efeito parcialmente agrupado: encolhimento Bayes-empírico para a média das UFs (τ² por momentos);
  o intercepto passa a ser o nível da "UF média", que é o que uma UF desconhecida recebe;
- covariância de Laplace (Hessiano no ótimo) → intervalo de credibilidade de p por caso (incerteza do modelo,
  não do resultado);
- acordos históricos ficam fora do treino (não são sentenças); métricas são out-of-fold (5 folds), inclusive o
  custo de decisão em R$ sob um cenário fixo — a métrica que importa para a política.
SegmentTable — p previsto por célula (sub × 4 docs × UF) com o n observado: a política em forma de planilha.
`SegmentTable.ajustar` (média empírica com shrinkage, o estimador da v1) continua disponível para comparação.
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
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score
from sklearn.model_selection import StratifiedKFold

from enteros import config as cfg
from enteros.data.load import carregar_base
from enteros.policy import custos
from enteros.policy.params import Politica, carregar_politica
from enteros.util import json_dumps

log = logging.getLogger(__name__)

CHAVE_PAI = ["sub_assunto", *cfg.DOCS_PREDITIVOS]
CHAVE_SEGMENTO = [*CHAVE_PAI, "uf"]
K_SHRINK = 20.0  # peso do pai em pseudo-observações (estimador empírico da v1)
C_REG = 10.0  # regularização L2 da logística (1/C no Hessiano)
N_FOLDS = 5
COL_SUB = "sub_golpe"
COL_INTERCEPTO = "intercepto"
PREFIXO_UF = "uf_"
UF_REFERENCIA = cfg.UFS[0]  # dummy omitida no ajuste; depois tudo é reexpresso em torno da UF média
DOCS_NULOS = tuple(d for d in cfg.DOCS if d not in cfg.DOCS_PREDITIVOS)  # exportados com coeficiente 0
TAU2_MIN = 1e-6
ORIGEM_MODELO = "modelo"
ORIGEM_EMPIRICA = "empirica"


def _chave(valores: list) -> str:
    return "|".join(str(v) for v in valores)


def _col_uf(uf: str) -> str:
    return f"{PREFIXO_UF}{uf}"


def _sigmoide(z: np.ndarray | float) -> np.ndarray | float:
    return 1.0 / (1.0 + np.exp(-z))


def _logit(p: float) -> float:
    p = min(max(p, 1e-12), 1 - 1e-12)
    return float(np.log(p / (1 - p)))


def _matriz(base: pd.DataFrame, colunas: list[str] | None = None) -> tuple[pd.DataFrame, list[str]]:
    """Desenho exportado: 6 docs, sub_golpe e uma dummy por UF (todas; o intercepto é a UF média)."""
    x = pd.DataFrame({d: base[d].astype(float) for d in cfg.DOCS})
    x[COL_SUB] = (base["sub_assunto"] == cfg.SUB_GOLPE).astype(float)
    for uf in cfg.UFS:
        x[_col_uf(uf)] = (base["uf"] == uf).astype(float)
    if colunas is not None:
        x = x.reindex(columns=colunas, fill_value=0.0)
    return x, list(x.columns)


def colunas_ajuste(colunas: list[str]) -> list[str]:
    """Colunas realmente ajustadas: sem dossiê/laudo e sem a dummy da UF de referência."""
    return [c for c in colunas if c not in DOCS_NULOS and c != _col_uf(UF_REFERENCIA)]


def folds_padrao(x: pd.DataFrame, y: np.ndarray) -> list[tuple[np.ndarray, np.ndarray]]:
    return list(StratifiedKFold(N_FOLDS, shuffle=True, random_state=cfg.SEMENTE).split(x, y))


def prever_oof(x: pd.DataFrame, y: np.ndarray, folds: list | None = None, c: float = C_REG) -> tuple[np.ndarray, np.ndarray]:
    """p out-of-fold e o fold de cada linha (mesmos folds para qualquer modelo comparado)."""
    folds = folds or folds_padrao(x, y)
    oof = np.zeros(len(y))
    fold = np.zeros(len(y), dtype=int)
    for k, (tr, te) in enumerate(folds):
        m = LogisticRegression(max_iter=3000, C=c).fit(x.iloc[tr], y[tr])
        oof[te] = m.predict_proba(x.iloc[te])[:, 1]
        fold[te] = k
    return oof, fold


def calibracao_por_decil(p: np.ndarray, y: np.ndarray) -> tuple[list[dict], float]:
    bins = pd.cut(p, np.linspace(0, 1, 11), include_lowest=True)
    cal = (pd.DataFrame({"p": p, "y": y, "b": bins}).groupby("b", observed=True)
           .agg(n=("y", "size"), p_prevista=("p", "mean"), taxa_real=("y", "mean")))
    ece = float((cal["n"] / cal["n"].sum() * (cal["p_prevista"] - cal["taxa_real"]).abs()).sum())
    linhas = [{"p_min": float(b.left), "p_max": float(b.right), "n": int(r.n),
               "p_prevista": float(r.p_prevista), "taxa_real": float(r.taxa_real)} for b, r in cal.iterrows()]
    return linhas, ece


def metricas_de(p: np.ndarray, y: np.ndarray) -> dict[str, float]:
    _, ece = calibracao_por_decil(p, y)
    return {
        "auc_oof": float(roc_auc_score(y, p)),
        "logloss_oof": float(log_loss(y, p)),
        "brier_oof": float(brier_score_loss(y, p)),
        "acuracia_oof_0.5": float(((p > 0.5) == y).mean()),
        "ece_oof": ece,
    }


def _laplace_cov(x: np.ndarray, y: np.ndarray, beta: np.ndarray, c: float) -> np.ndarray:
    """Inversa do Hessiano da log-posterior no ótimo: XᵀWX + I/C (intercepto sem penalidade, como no sklearn)."""
    xd = np.c_[np.ones(len(x)), x]
    p = _sigmoide(xd @ beta)
    w = p * (1 - p)
    h = (xd * w[:, None]).T @ xd + np.diag(np.r_[0.0, np.full(x.shape[1], 1.0 / c)])
    return np.linalg.inv(h)


def _encolher_uf(coef_fit: dict[str, float], se_fit: dict[str, float], n_por_uf: pd.Series) -> tuple[dict[str, dict], float, float]:
    """Efeitos de UF (referência = 0) → encolhimento Bayes-empírico para a média das UFs com dados.

    τ² = var(efeitos) − média(SE²) (momentos). A UF de referência não tem SE próprio no desenho; usa o SE médio
    (aproximação declarada). UF sem linhas recebe a média (desvio 0).
    """
    brutos = {uf: float(coef_fit.get(_col_uf(uf), 0.0)) for uf in cfg.UFS}
    ses = {uf: se_fit.get(_col_uf(uf)) for uf in cfg.UFS}
    ses[UF_REFERENCIA] = float(np.mean([s for s in ses.values() if s is not None]))
    com_dados = [uf for uf in cfg.UFS if int(n_por_uf.get(uf, 0)) > 0]
    e = np.array([brutos[u] for u in com_dados])
    s = np.array([ses[u] for u in com_dados])
    media = float(e.mean())
    tau2 = max(float(e.var(ddof=1) - np.mean(s**2)), TAU2_MIN)
    efeitos: dict[str, dict] = {}
    for uf in cfg.UFS:
        if uf in com_dados:
            fator = tau2 / (tau2 + ses[uf] ** 2)
            enc = media + (brutos[uf] - media) * fator
            efeitos[uf] = {"n": int(n_por_uf[uf]), "bruto": brutos[uf], "se": ses[uf], "fator": float(fator),
                           "encolhido": float(enc), "desvio": float(enc - media)}
        else:
            efeitos[uf] = {"n": 0, "bruto": None, "se": None, "fator": 0.0, "encolhido": media, "desvio": 0.0}
    return efeitos, media, float(np.sqrt(tau2))


def _q_doc(base: pd.DataFrame) -> dict[str, dict[str, float]]:
    """P(doc presente | padrão dos outros 3 docs preditivos): proxy da chance de o back-office localizá-lo."""
    out: dict[str, dict[str, float]] = {}
    for d in cfg.DOCS_PREDITIVOS:
        outros = [o for o in cfg.DOCS_PREDITIVOS if o != d]
        padrao = base[outros].astype(int).astype(str).agg("".join, axis=1)
        out[d] = {str(k): float(v) for k, v in base.groupby(padrao)[d].mean().items()}
    return out


@dataclass
class ModeloPerda:
    colunas: list[str]
    coef: list[float]
    intercepto: float
    metricas: dict = field(default_factory=dict)
    calibracao: list[dict] = field(default_factory=list)
    versao: str = ""
    medias: dict[str, float] = field(default_factory=dict)  # média de cada coluna na base (referência das contribuições)
    # v2 — todos com default para que JSONs antigos continuem carregando
    colunas_cov: list[str] = field(default_factory=list)  # [intercepto, colunas ajustadas] (UF em relação à referência)
    cov: list[list[float]] = field(default_factory=list)
    se: dict[str, float] = field(default_factory=dict)
    efeitos_uf: dict[str, dict] = field(default_factory=dict)
    tau_uf: float = 0.0
    media_uf: float = 0.0
    q_doc: dict[str, dict[str, float]] = field(default_factory=dict)
    regularizacao_c: float = C_REG

    # ---------- ajuste ----------
    @classmethod
    def ajustar(cls, base: pd.DataFrame, versao: str, politica: Politica | None = None) -> "ModeloPerda":
        politica = politica or carregar_politica()
        treino = base[base["acordo"] == 0] if "acordo" in base.columns else base
        x_full, colunas = _matriz(treino)
        cols_fit = colunas_ajuste(colunas)
        x = x_full[cols_fit]
        y = treino["perda"].to_numpy()

        oof, _ = prever_oof(x, y)
        metricas = metricas_de(oof, y)
        calib, _ = calibracao_por_decil(oof, y)
        custo = custos.custo_regra_fixa(oof, treino, politica)

        final = LogisticRegression(max_iter=3000, C=C_REG).fit(x, y)
        beta = np.r_[final.intercept_[0], final.coef_[0]]
        cov = _laplace_cov(x.to_numpy(), y, beta, C_REG)
        colunas_cov = [COL_INTERCEPTO, *cols_fit]
        se = dict(zip(colunas_cov, np.sqrt(np.diag(cov)).tolist(), strict=True))
        coef_fit = dict(zip(cols_fit, beta[1:].tolist(), strict=True))
        efeitos_uf, media_uf, tau = _encolher_uf(coef_fit, se, treino["uf"].value_counts())

        coef: list[float] = []
        for c in colunas:
            if c in DOCS_NULOS:
                coef.append(0.0)
            elif c.startswith(PREFIXO_UF):
                coef.append(efeitos_uf[c[len(PREFIXO_UF):]]["desvio"])
            else:
                coef.append(coef_fit[c])

        com_dados = [e for e in efeitos_uf.values() if e["n"] > 0]
        metricas.update({
            "n_treino": int(len(y)),
            "n_acordos_excluidos": int(len(base) - len(treino)),
            "taxa_perda_base": float(y.mean()),
            "tau_uf": tau,
            "encolhimento_uf_medio": float(np.mean([e["fator"] for e in com_dados])),
            "custo_decisao_oof": custo["custo_total"],
            "custo_defender_tudo": custo["custo_defender_tudo"],
            "share_acordo_oof": custo["share_acordo"],
        })
        return cls(colunas=colunas, coef=coef, intercepto=float(beta[0] + media_uf), metricas=metricas,
                   calibracao=calib, versao=versao, medias={c: float(v) for c, v in x_full.mean().items()},
                   colunas_cov=colunas_cov, cov=cov.tolist(), se=se, efeitos_uf=efeitos_uf, tau_uf=tau,
                   media_uf=media_uf, q_doc=_q_doc(base))

    # ---------- predição ----------
    def _linha(self, sub_assunto: str, flags: dict[str, int], uf: str) -> dict[str, float]:
        linha = {d: float(flags[d]) for d in cfg.DOCS}
        linha[COL_SUB] = float(sub_assunto == cfg.SUB_GOLPE)
        for c in self.colunas:
            if c.startswith(PREFIXO_UF):
                linha[c] = float(c == _col_uf(uf))  # UF desconhecida → todas 0 → nível da UF média
        return linha

    def logit(self, sub_assunto: str, flags: dict[str, int], uf: str) -> float:
        linha = self._linha(sub_assunto, flags, uf)
        return float(self.intercepto + sum(c * linha[col] for col, c in zip(self.colunas, self.coef, strict=True)))

    def p_perda(self, sub_assunto: str, flags: dict[str, int], uf: str) -> float:
        return float(_sigmoide(self.logit(sub_assunto, flags, uf)))

    def _vetor_cov(self, sub_assunto: str, flags: dict[str, int], uf: str) -> np.ndarray:
        """Vetor de desenho na parametrização da covariância. UF desconhecida = média das dummies."""
        v = []
        for c in self.colunas_cov:
            if c == COL_INTERCEPTO:
                v.append(1.0)
            elif c in cfg.DOCS:
                v.append(float(flags[c]))
            elif c == COL_SUB:
                v.append(float(sub_assunto == cfg.SUB_GOLPE))
            elif uf in cfg.UFS:
                v.append(float(c == _col_uf(uf)))
            else:
                v.append(1.0 / len(cfg.UFS))
        return np.array(v)

    def p_perda_intervalo(self, sub_assunto: str, flags: dict[str, int], uf: str, z: float = cfg.Z_IC95) -> tuple[float, float]:
        """Intervalo de credibilidade de p (Laplace): incerteza dos coeficientes, centrada no p exportado."""
        p = self.p_perda(sub_assunto, flags, uf)
        if not self.cov:
            return p, p
        x = self._vetor_cov(sub_assunto, flags, uf)
        sd = float(np.sqrt(max(x @ np.asarray(self.cov) @ x, 0.0)))
        zc = _logit(p)
        return float(_sigmoide(zc - z * sd)), float(_sigmoide(zc + z * sd))

    def q_doc_para(self, doc: str, flags: dict[str, int], padrao: float) -> float:
        """Chance de localizar `doc` dado o padrão dos outros docs preditivos; `padrao` se o padrão não existe."""
        outros = [o for o in cfg.DOCS_PREDITIVOS if o != doc]
        chave = "".join(str(int(flags[o])) for o in outros)
        return float(self.q_doc.get(doc, {}).get(chave, padrao))

    def contribuicoes(self, sub_assunto: str, flags: dict[str, int], uf: str, top: int = 5) -> list[dict]:
        """coef × (valor − média da base), em log-odds de PERDA. Positivo = aumenta o risco do banco em relação
        ao caso médio; negativo = protege. Documento ausente aparece como risco, presente como proteção."""
        linha = self._linha(sub_assunto, flags, uf)
        itens = []
        for col, c in zip(self.colunas, self.coef, strict=True):
            contrib = c * (linha[col] - self.medias.get(col, 0.0))
            if col in cfg.DOCS:
                nome, valor = cfg.NOME_DOC[col], ("presente" if flags[col] else "ausente")
            elif col == COL_SUB:
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
        return _sigmoide(z)

    # ---------- persistência ----------
    def to_json(self, caminho: Path) -> None:
        caminho.parent.mkdir(parents=True, exist_ok=True)
        caminho.write_text(json_dumps(self.__dict__), encoding="utf-8")

    @classmethod
    def from_json(cls, caminho: Path) -> "ModeloPerda":
        return cls(**json.loads(caminho.read_text(encoding="utf-8")))


@dataclass
class SegmentTable:
    pai: dict[str, dict]  # chave pai -> {n, p, p_bruto}
    seg: dict[str, dict]  # chave segmento -> {n, p_bruto, p}
    p_global: float
    origem: str = ORIGEM_MODELO

    @staticmethod
    def _flags(valores: list) -> dict[str, int]:
        flags = dict.fromkeys(cfg.DOCS, 0)
        flags.update({d: int(v) for d, v in zip(cfg.DOCS_PREDITIVOS, valores, strict=True)})
        return flags

    @classmethod
    def derivar(cls, modelo: ModeloPerda, base: pd.DataFrame) -> "SegmentTable":
        """p previsto pelo modelo em cada célula observada, com o n e a taxa bruta da base (a política em planilha)."""
        sent = base[base["acordo"] == 0] if "acordo" in base.columns else base
        pai_d: dict[str, dict] = {}
        for k, (n, pb) in sent.groupby(CHAVE_PAI)["perda"].agg(["size", "mean"]).iterrows():
            sub, *vals = k
            pai_d[_chave(list(k))] = {"n": int(n), "p_bruto": float(pb), "p": modelo.p_perda(sub, cls._flags(vals), "")}
        seg_d: dict[str, dict] = {}
        for k, (n, pb) in sent.groupby(CHAVE_SEGMENTO)["perda"].agg(["size", "mean"]).iterrows():
            sub, *vals, uf = k
            seg_d[_chave(list(k))] = {"n": int(n), "p_bruto": float(pb), "p": modelo.p_perda(sub, cls._flags(vals), uf)}
        return cls(pai=pai_d, seg=seg_d, p_global=float(sent["perda"].mean()), origem=ORIGEM_MODELO)

    @classmethod
    def ajustar(cls, base: pd.DataFrame, k_shrink: float = K_SHRINK) -> "SegmentTable":
        """Estimador empírico da v1: taxa observada por célula com shrinkage para o pai. Mantido para comparação."""
        sent = base[base["acordo"] == 0] if "acordo" in base.columns else base
        p_global = float(sent["perda"].mean())
        pai = sent.groupby(CHAVE_PAI)["perda"].agg(["size", "mean"])
        pai_d = {_chave(list(k)): {"n": int(n), "p": float(p), "p_bruto": float(p)} for k, (n, p) in pai.iterrows()}
        seg_d: dict[str, dict] = {}
        for k, (n, p) in sent.groupby(CHAVE_SEGMENTO)["perda"].agg(["size", "mean"]).iterrows():
            p_pai = pai_d.get(_chave(list(k[:-1])), {"p": p_global})["p"]
            seg_d[_chave(list(k))] = {"n": int(n), "p_bruto": float(p), "p": float((n * p + k_shrink * p_pai) / (n + k_shrink))}
        return cls(pai=pai_d, seg=seg_d, p_global=p_global, origem=ORIGEM_EMPIRICA)

    def p_perda(self, sub_assunto: str, flags: dict[str, int], uf: str) -> tuple[float, int]:
        """Devolve (p, n do segmento). Cai para o pai e depois para o global se o segmento não existir."""
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
        caminho.write_text(json_dumps({"chave_pai": CHAVE_PAI, "chave_segmento": CHAVE_SEGMENTO, "origem": self.origem,
                                       "p_global": self.p_global, "pai": self.pai, "seg": self.seg}), encoding="utf-8")

    @classmethod
    def from_json(cls, caminho: Path) -> "SegmentTable":
        d = json.loads(caminho.read_text(encoding="utf-8"))
        return cls(pai=d["pai"], seg=d["seg"], p_global=d["p_global"], origem=d.get("origem", ORIGEM_EMPIRICA))


def treinar(base: pd.DataFrame, versao: str, politica: Politica | None = None) -> tuple[SegmentTable, ModeloPerda]:
    mod = ModeloPerda.ajustar(base, versao, politica)
    return SegmentTable.derivar(mod, base), mod


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
    print(pd.DataFrame(mod.efeitos_uf).T.dropna().sort_values("encolhido", ascending=False).round(3).head(6).to_string())
    print(f"segmentos: {len(seg.seg)}  pais: {len(seg.pai)}  origem: {seg.origem}  → {cfg.DIR_MODELS}")


if __name__ == "__main__":
    main()
