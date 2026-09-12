"""Replay da política sobre a base histórica com RESULTADOS REAIS.

Custo real de ter defendido = custo do escritório + [perdeu]·(condenação·(1+honorários)·tempo + custas).
Custo sob a política = para casos recomendados a acordo, a·(oferta + op) + (1−a)·(custo real de defender + op);
para casos recomendados a defesa, o custo real. `a` vem da curva de aceite (premissa) ou é fixado na sensibilidade.
Baselines: defender tudo (o que aconteceu) e acordar tudo.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from enteros import config as cfg
from enteros.policy.engine import Engine
from enteros.policy.negotiation import p_aceite


def pontuar_base(base: pd.DataFrame, eng: Engine) -> pd.DataFrame:
    """Adiciona p_perda (logística in-sample; a métrica honesta está em modelo.metricas OOF), EV e escada vetorizados."""
    df = base.copy()
    pol = eng.politica
    c, o = pol.custos, pol.oferta
    df["p_perda_hat"] = eng.modelo.p_perda_lote(df)
    ratio_media = np.array([eng.ratio.para(uf, sub)["media"] for uf, sub in zip(df["uf"], df["sub_assunto"])])
    df["cond_esperada_se_perde"] = ratio_media * df["valor_causa"]
    custo_se_perde = (df["cond_esperada_se_perde"] * (1 + c.honorarios_sucumbencia_pct) * c.fator_tempo
                      + c.custas_pct_valor_causa * df["valor_causa"])
    df["ev_defesa"] = c.custo_escritorio_defesa + df["p_perda_hat"] * custo_se_perde
    # escada vetorizada: alvo = argmin na grade de frações do VC dentro de [piso, teto]
    grade = np.arange(o.piso_pct_causa, o.teto_pct_causa + 1e-9, o.grade_passo)
    pa = p_aceite(grade, o)  # (G,)
    vc = df["valor_causa"].to_numpy()[:, None]
    ofertas = grade[None, :] * vc  # (N, G)
    teto = np.minimum(df["ev_defesa"].to_numpy() * (1 - o.margem_teto), o.teto_pct_causa * vc[:, 0])
    piso = o.piso_pct_causa * vc[:, 0]
    custo = pa[None, :] * (ofertas + c.custo_escritorio_acordo) + (1 - pa[None, :]) * (df["ev_defesa"].to_numpy()[:, None] + c.custo_escritorio_acordo)
    custo = np.where((ofertas <= teto[:, None] + 1e-9) & (ofertas >= piso[:, None] - 1e-9), custo, np.inf)
    idx = np.argmin(custo, axis=1)
    df["alvo"] = np.where(np.isfinite(custo[np.arange(len(df)), idx]), ofertas[np.arange(len(df)), idx], piso)
    df["p_aceite_alvo"] = p_aceite(df["alvo"] / df["valor_causa"], o)
    df["ev_acordo"] = df["p_aceite_alvo"] * df["alvo"] + (1 - df["p_aceite_alvo"]) * df["ev_defesa"] + c.custo_escritorio_acordo
    f = pol.faixas
    df["decisao"] = np.select(
        [df["p_perda_hat"] > f.limiar_vermelha, df["p_perda_hat"] < f.limiar_verde, df["ev_acordo"] < df["ev_defesa"]],
        [cfg.DECISAO_ACORDO, cfg.DECISAO_DEFESA, cfg.DECISAO_ACORDO], default=cfg.DECISAO_DEFESA)
    df["faixa"] = np.select([df["p_perda_hat"] > f.limiar_vermelha, df["p_perda_hat"] < f.limiar_verde],
                            [cfg.FAIXA_VERMELHA, cfg.FAIXA_VERDE], default=cfg.FAIXA_AMARELA)
    # custo REAL de ter defendido (o que aconteceu)
    df["custo_real_defesa"] = c.custo_escritorio_defesa + df["perda"] * (
        df["valor_condenacao"] * (1 + c.honorarios_sucumbencia_pct) * c.fator_tempo + c.custas_pct_valor_causa * df["valor_causa"])
    return df


def custo_politica(df: pd.DataFrame, eng: Engine, taxa_aceite: float | None = None, mult_oferta: float = 1.0) -> pd.Series:
    """Custo por caso sob a política. taxa_aceite=None usa a curva; senão fixa a taxa (sensibilidade)."""
    c = eng.politica.custos
    oferta = df["alvo"] * mult_oferta
    a = df["p_aceite_alvo"] if taxa_aceite is None else pd.Series(taxa_aceite, index=df.index)
    acordo = a * oferta + (1 - a) * df["custo_real_defesa"] + c.custo_escritorio_acordo
    return pd.Series(np.where(df["decisao"] == cfg.DECISAO_ACORDO, acordo, df["custo_real_defesa"]), index=df.index)


def resumo(df: pd.DataFrame, eng: Engine) -> dict:
    c = eng.politica.custos
    n = len(df)
    total_cond = float(df["valor_condenacao"].sum())
    total_defender_tudo = float(df["custo_real_defesa"].sum())
    a_all = df["p_aceite_alvo"]
    acordar_tudo = float((a_all * df["alvo"] + (1 - a_all) * df["custo_real_defesa"] + c.custo_escritorio_acordo).sum())
    politica = float(custo_politica(df, eng).sum())
    sens = []
    for ta in (0.5, 0.6, 0.7, 0.8, None):
        for mult in (0.8, 1.0, 1.2):
            custo = float(custo_politica(df, eng, ta, mult).sum())
            sens.append({"taxa_aceite": "curva" if ta is None else ta, "mult_oferta": mult,
                         "custo": custo, "economia": total_defender_tudo - custo,
                         "economia_pct": (total_defender_tudo - custo) / total_defender_tudo})
    por_faixa = (df.groupby("faixa").agg(n=("numero", "size"), share=("numero", lambda s: len(s) / n),
                                          p_perda_prevista=("p_perda_hat", "mean"), perda_real=("perda", "mean"),
                                          condenacao_real=("valor_condenacao", "sum"),
                                          custo_real_defesa=("custo_real_defesa", "sum"))
                 .reset_index().to_dict(orient="records"))
    # valor da informação agregado: recuperar cada doc preditivo ausente
    voi = {}
    for d in cfg.DOCS_PREDITIVOS:
        sem = df[df[d] == 0]
        if sem.empty:
            continue
        df2 = sem.copy()
        df2[d] = 1
        p2 = eng.modelo.p_perda_lote(df2)
        custo_se_perde = (sem["cond_esperada_se_perde"] * (1 + c.honorarios_sucumbencia_pct) * c.fator_tempo
                          + c.custas_pct_valor_causa * sem["valor_causa"])
        ev2 = c.custo_escritorio_defesa + p2 * custo_se_perde
        voi[d] = {"casos_sem": int(len(sem)), "ganho_total": float((sem["ev_defesa"] - ev2).sum()),
                  "ganho_por_caso": float((sem["ev_defesa"] - ev2).mean())}
    # efeito marginal observado de cada doc (win rate com/sem) — para o slide "dossiê e laudo não movem"
    efeito_docs = {d: {"perda_com": float(df.loc[df[d] == 1, "perda"].mean()), "perda_sem": float(df.loc[df[d] == 0, "perda"].mean())}
                   for d in cfg.DOCS}
    return {
        "n_casos": n, "base_real": bool(n >= 50000),
        "condenacao_total": total_cond, "condenacao_por_caso": total_cond / n,
        "custo_defender_tudo": total_defender_tudo, "custo_acordar_tudo": acordar_tudo,
        "custo_politica_curva": politica, "economia_politica_curva": total_defender_tudo - politica,
        "economia_pct_curva": (total_defender_tudo - politica) / total_defender_tudo,
        "share_acordo": float((df["decisao"] == cfg.DECISAO_ACORDO).mean()),
        "sensibilidade": sens, "por_faixa": por_faixa, "voi": voi, "efeito_docs": efeito_docs,
        "metricas_modelo": eng.modelo.metricas, "calibracao": eng.modelo.calibracao,
        "politica_versao": eng.politica.versao, "modelo_versao": eng.modelo.versao,
        "premissas": eng.politica.model_dump(),
    }
