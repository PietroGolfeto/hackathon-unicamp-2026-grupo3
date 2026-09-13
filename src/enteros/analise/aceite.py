"""Curva de aceite bayesiana: posterior em grade sobre (s50, largura) com verossimilhança censurada por intervalo na
escada (aceitou no degrau k ⇒ limiar do autor ∈ (o_{k−1}, o_k]; recusou tudo ⇒ limiar > teto) e simulador que mostra
em quantos acordos a curva se aprende. Só leitura: o policy.yaml segue com a premissa H1 até haver dados reais; este
módulo é o que o monitoramento vai rodar sobre os resultados registrados no portal.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from enteros import config as cfg  # noqa: E402
from enteros.analise.comum import custo_realizado, engine_com  # noqa: E402
from enteros.policy.engine import Engine  # noqa: E402

S50_GRADE = np.round(np.arange(0.15, 0.601, 0.01), 3)
LARGURA_GRADE = np.round(np.arange(0.02, 0.151, 0.01), 3)
PRIOR_S50_SD = 0.10  # prior fraco em torno da premissa H1 (declarado)
MUNDOS_PADRAO = ((0.38, 0.08), (0.25, 0.05))  # (s50, largura) verdadeiros: um pior e um melhor que o assumido
MARCOS = (50, 100, 300, 500, 1000)
PASSO = 25


class PosteriorAceite:
    """Posterior em grade de (s50, largura) da curva logística de aceite."""

    def __init__(self, s50_prior: float, sd_prior: float = PRIOR_S50_SD) -> None:
        self.S, self.W = np.meshgrid(S50_GRADE, LARGURA_GRADE, indexing="ij")
        self.logpost = -0.5 * ((self.S - s50_prior) / sd_prior) ** 2
        self.n = 0

    def _F(self, oferta: float) -> np.ndarray:
        return 1.0 / (1.0 + np.exp(-(oferta - self.S) / self.W))

    def atualizar(self, degraus: Sequence[float], aceito_em: int | None) -> None:
        """`degraus` crescentes (frações do VC); `aceito_em` = índice do degrau aceito; None = recusou todos."""
        if aceito_em is None:
            lik = 1.0 - self._F(degraus[-1])
        else:
            lik = self._F(degraus[aceito_em]) - (self._F(degraus[aceito_em - 1]) if aceito_em > 0 else 0.0)
        self.logpost = self.logpost + np.log(np.clip(lik, 1e-12, None))
        self.n += 1

    def pesos(self) -> np.ndarray:
        w = np.exp(self.logpost - self.logpost.max())
        return w / w.sum()

    def resumo(self) -> dict[str, float]:
        w = self.pesos()
        s50 = float((w * self.S).sum())
        sd = float(np.sqrt((w * (self.S - s50) ** 2).sum()))
        marg = w.sum(axis=1)
        acum = np.cumsum(marg)
        lo = float(S50_GRADE[np.searchsorted(acum, 0.05)])
        hi = float(S50_GRADE[min(np.searchsorted(acum, 0.95), len(S50_GRADE) - 1)])
        return {"n": self.n, "s50_media": s50, "s50_sd": sd, "s50_ic90": [lo, hi], "largura_media": float((w * self.W).sum())}

    def curva(self, ofertas: np.ndarray) -> np.ndarray:
        """Probabilidade de aceite preditiva (média posterior) em cada oferta."""
        w = self.pesos()
        return np.array([float((w * self._F(o)).sum()) for o in ofertas])


def escadas_da_base(df: pd.DataFrame, eng: Engine) -> pd.DataFrame:
    """Escadas (abertura, alvo, teto como frações do VC) dos casos que a política manda acordar."""
    o = eng.politica.oferta
    acordo = df[df["decisao"] == cfg.DECISAO_ACORDO]
    vc = acordo["valor_causa"].to_numpy(dtype=float)
    alvo = acordo["alvo"].to_numpy(dtype=float) / vc
    teto = np.minimum(acordo["ev_defesa"].to_numpy(dtype=float) * (1 - o.margem_teto) / vc, o.teto_pct_causa)
    teto = np.maximum(teto, alvo)
    abertura = np.maximum(o.piso_pct_causa, alvo * (1 - o.desconto_abertura))
    return pd.DataFrame({"abertura": abertura, "alvo": alvo, "teto": teto})


def simular(escadas: pd.DataFrame, eng: Engine, s50_true: float, largura_true: float, n: int,
            semente: int = cfg.SEMENTE, passo: int = PASSO) -> tuple[pd.DataFrame, PosteriorAceite]:
    """Autores com limiar logístico(s50_true, largura_true) respondem à escada (ou a uma banda de exploração)."""
    pol = eng.politica
    rng = np.random.default_rng(semente)
    post = PosteriorAceite(pol.oferta.aceite_s50)
    idx = rng.integers(0, len(escadas), n)
    u = rng.random(n)
    limiares = s50_true + largura_true * np.log(u / (1 - u))
    explorar = rng.random(n) < pol.experimento.fracao_exploracao
    bandas = rng.choice(pol.experimento.bandas_pct_causa, n)
    trajetoria = []
    for i in range(n):
        if explorar[i]:
            post.atualizar([float(bandas[i])], 0 if limiares[i] <= bandas[i] else None)
        else:
            e = escadas.iloc[idx[i]]
            degraus = [float(e["abertura"]), float(e["alvo"]), float(e["teto"])]
            aceito = next((k for k, d in enumerate(degraus) if limiares[i] <= d), None)
            post.atualizar(degraus, aceito)
        if (i + 1) % passo == 0 or i + 1 == n:
            trajetoria.append(post.resumo())
    return pd.DataFrame(trajetoria), post


def _fig(trajs: list[tuple[tuple[float, float], pd.DataFrame, PosteriorAceite]], eng: Engine, out: Path) -> None:
    o = eng.politica.oferta
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4.4))
    cores = ("#c62828", "#2e7d32", "#1565c0")
    for (s50, w), tr, _ in trajs:
        cor = cores[len(a1.lines) // 2 % len(cores)]
        a1.plot(tr["n"], tr["s50_media"], color=cor, lw=2, label=f"mundo s50 = {s50:.2f}: estimativa")
        a1.fill_between(tr["n"], [x[0] for x in tr["s50_ic90"]], [x[1] for x in tr["s50_ic90"]], color=cor, alpha=.15)
        a1.axhline(s50, color=cor, ls=":", lw=1)
    a1.axhline(o.aceite_s50, color="#171717", ls="--", lw=1, label=f"premissa inicial ({o.aceite_s50:.2f})")
    a1.set_xlabel("acordos propostos e registrados no portal")
    a1.set_ylabel("s50: fração do VC em que 50% aceitam")
    a1.set_title("A curva de aceite se aprende em poucas centenas de casos")
    a1.legend(fontsize=7)
    ofertas = np.linspace(0.10, 0.70, 61)
    a2.plot(ofertas, 1 / (1 + np.exp(-(ofertas - o.aceite_s50) / o.aceite_largura)), "--", color="#171717", label="premissa inicial")
    for (s50, w), tr, post in trajs[:1]:
        a2.plot(ofertas, 1 / (1 + np.exp(-(ofertas - s50) / w)), color="#c62828", lw=2, label=f"mundo verdadeiro (s50 {s50:.2f})")
        a2.plot(ofertas, post.curva(ofertas), color="#ffae35", lw=2, label=f"aprendida após {post.n} acordos")
    a2.set_xlabel("oferta (fração do valor da causa)")
    a2.set_ylabel("probabilidade de o autor aceitar")
    a2.set_title("Premissa × mundo × curva aprendida")
    a2.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(out / "aprendizado_aceite.png", dpi=150)
    plt.close(fig)


def impacto_de_aprender(df: pd.DataFrame, eng: Engine, s50_true: float, largura_true: float) -> dict:
    """Se o mundo for (s50_true, largura_true): custo da política desenhada com a premissa × redesenhada com a curva certa."""
    premissa = custo_realizado(df, eng, s50_true, largura_true)
    aprendida = custo_realizado(df, engine_com(eng, aceite_s50=s50_true, aceite_largura=largura_true), s50_true, largura_true)
    return {"s50_mundo": s50_true, "largura_mundo": largura_true,
            "economia_pct_com_premissa": premissa["economia_pct"], "share_acordo_com_premissa": premissa["share_acordo"],
            "economia_pct_com_curva_aprendida": aprendida["economia_pct"], "share_acordo_com_curva_aprendida": aprendida["share_acordo"],
            "ganho_de_aprender": premissa["custo"] - aprendida["custo"]}


def analisar(df: pd.DataFrame, eng: Engine, out: Path, mundos: Sequence[tuple[float, float]] = MUNDOS_PADRAO,
             n: int = MARCOS[-1]) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    escadas = escadas_da_base(df, eng)
    trajs, marcos, impactos = [], [], []
    for s50, w in mundos:
        tr, post = simular(escadas, eng, s50, w, n)
        trajs.append(((s50, w), tr, post))
        for m in MARCOS:
            linha = tr[tr["n"] == m]
            if len(linha):
                r = linha.iloc[0]
                marcos.append({"s50_mundo": s50, "largura_mundo": w, "n": int(m), "s50_media": float(r["s50_media"]),
                               "s50_sd": float(r["s50_sd"]), "s50_ic90": list(r["s50_ic90"]), "erro": float(r["s50_media"] - s50)})
        impactos.append(impacto_de_aprender(df, eng, s50, w))
    _fig(trajs, eng, out)
    return {"prior": {"s50": eng.politica.oferta.aceite_s50, "sd": PRIOR_S50_SD, "largura": "uniforme"},
            "exploracao": eng.politica.experimento.model_dump(), "n_escadas": int(len(escadas)),
            "marcos": marcos, "impacto": impactos,
            "trajetorias": {f"{s50:.2f}": tr.assign(s50_ic90=tr["s50_ic90"].astype(str)).to_dict(orient="records") for (s50, _), tr, _ in trajs}}
