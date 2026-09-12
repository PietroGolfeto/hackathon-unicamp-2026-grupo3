"""Replay da política sobre a base histórica com RESULTADOS REAIS e probabilidade OUT-OF-FOLD.

Custo real de ter defendido = escritório + [perdeu]·(condenação·(1 + honorários)·tempo + custas).
Custo sob a política = em acordo: a·oferta + (1 − a)·custo real de defender + operacional; em defesa: custo real.
`a` vem da curva de aceite (premissa H1) ou é fixado (sensibilidade). O lado defesa é fato; o lado acordo é hipótese.
Baselines: defender tudo (o que aconteceu), acordar tudo, heurísticas de documento, limiar fixo (grupos da UFMG) e
oráculo (resultado conhecido) — o teto do que qualquer modelo pode capturar.
"""

from __future__ import annotations

from itertools import product

import numpy as np
import pandas as pd

from enteros import config as cfg
from enteros.policy import custos as cst
from enteros.policy.engine import Engine
from enteros.policy.model import _matriz, colunas_ajuste, prever_oof
from enteros.policy.negotiation import escada_lote, p_aceite
from enteros.policy.params import Custos

N_MIN_OOF = 1000
N_BOOTSTRAP = 200
DOCS_INSTRUIR = cfg.DOCS_CRITICOS  # conjunto avaliado no backtest (contrato, extrato)
LIMIAR_UFMG = 0.60  # regra "p_perda > 0,60 → acordo" usada por três grupos da edição anterior
MULT_Q = (0.5, 0.75, 1.0)
S50_SENSIBILIDADE = (0.25, 0.30, 0.40, 0.50)
ACEITES_SENSIBILIDADE = (0.5, 0.6, 0.7, 0.8, None)
MULT_OFERTA_SENSIBILIDADE = (0.8, 1.0, 1.2)


def _sigmoide(z: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-z))


def _logit(p: np.ndarray) -> np.ndarray:
    p = np.clip(p, 1e-9, 1 - 1e-9)
    return np.log(p / (1 - p))


# ---------------------------------------------------------------- probabilidade e avaliação

def p_oof(base: pd.DataFrame, eng: Engine) -> tuple[np.ndarray, np.ndarray]:
    """p de perda out-of-fold (mesmos 5 folds do treino) para as sentenças; acordos históricos ficam in-sample (fold −1)."""
    p = np.asarray(eng.modelo.p_perda_lote(base), dtype=float)
    fold = np.full(len(base), -1, dtype=int)
    sent = (base["acordo"] == 0).to_numpy() if "acordo" in base.columns else np.ones(len(base), dtype=bool)
    y = base.loc[sent, "perda"].to_numpy()
    if sent.sum() >= N_MIN_OOF and y.min() != y.max():
        x_full, colunas = _matriz(base.loc[sent])
        oof, f = prever_oof(x_full[colunas_ajuste(colunas)], y)
        p[sent], fold[sent] = oof, f
    return p, fold


def _ratio_media(df: pd.DataFrame, eng: Engine) -> np.ndarray:
    pares = df["uf"].astype(str) + "|" + df["sub_assunto"].astype(str)
    cache = {k: eng.ratio.para(*k.split("|", 1))["media"] for k in pares.unique()}
    return pares.map(cache).to_numpy(dtype=float)


def avaliar(df: pd.DataFrame, eng: Engine, p: np.ndarray, custos: Custos | None = None,
            s50: float | None = None) -> dict[str, np.ndarray]:
    """EV, escada, decisão binária (faixas + custo esperado) e breakeven, vetorizados. Usa `p` como probabilidade."""
    pol = eng.politica
    c, o = custos or pol.custos, pol.oferta
    vc = df["valor_causa"].to_numpy(dtype=float)
    ratio = df["ratio_media"].to_numpy(dtype=float) if "ratio_media" in df.columns else _ratio_media(df, eng)
    csp = cst.custo_se_perde(ratio, vc, c)
    ev_def = cst.ev_defesa(p, csp, c)
    alvo, pa = escada_lote(ev_def, vc, o, c, 0.0, s50)
    ev_aco = cst.ev_acordo(alvo, pa, ev_def, c)
    f = pol.faixas
    decisao = np.select([p > f.limiar_vermelha, p < f.limiar_verde, ev_aco < ev_def],
                        [cfg.DECISAO_ACORDO, cfg.DECISAO_DEFESA, cfg.DECISAO_ACORDO], default=cfg.DECISAO_DEFESA)
    faixa = np.select([p > f.limiar_vermelha, p < f.limiar_verde], [cfg.FAIXA_VERMELHA, cfg.FAIXA_VERDE],
                      default=cfg.FAIXA_AMARELA)
    return {"ratio_media": ratio, "custo_se_perde": csp, "ev_defesa": ev_def, "alvo": alvo, "p_aceite_alvo": pa,
            "ev_acordo": ev_aco, "decisao": decisao, "faixa": faixa,
            "p_breakeven": cst.breakeven(alvo, pa, csp, c)}


def custo_real(df: pd.DataFrame, custos: Custos) -> np.ndarray:
    return np.asarray(cst.custo_real_defesa(df["perda"].to_numpy(), df["valor_condenacao"].to_numpy(),
                                            df["valor_causa"].to_numpy(), custos), dtype=float)


def _instruir(df: pd.DataFrame, eng: Engine, p: np.ndarray, av: dict[str, np.ndarray], mult_q: float = 1.0) -> tuple[np.ndarray, np.ndarray]:
    """EVSI de pedir os docs críticos ausentes (contrato/extrato) antes de acordar, por linha, e a flag `instruir`.
    Mesma lógica do engine (probabilidade total por doc, deslocamentos em log-odds somados), vetorizada."""
    pol, c = eng.politica, eng.politica.custos
    coefs = dict(zip(eng.modelo.colunas, eng.modelo.coef, strict=True))
    z0 = _logit(p)
    q, dz_com, dz_falha, ausentes = {}, {}, {}, np.zeros(len(df))
    for d in DOCS_INSTRUIR:
        aus = (df[d] == 0).to_numpy()
        ausentes += aus
        outros = [o for o in cfg.DOCS_PREDITIVOS if o != d]
        padrao = df[outros].astype(int).astype(str).agg("".join, axis=1)
        q_d = padrao.map(eng.modelo.q_doc.get(d, {})).fillna(pol.faixas.q_doc_padrao).to_numpy(dtype=float)
        q[d] = np.where(aus, np.clip(q_d * mult_q, 0.0, 1.0), 1.0)
        dz_com[d] = np.where(aus, coefs[d], 0.0)
        p_com = _sigmoide(z0 + dz_com[d])
        with np.errstate(divide="ignore", invalid="ignore"):
            p_falha = np.where(q[d] < 1, (p - q[d] * p_com) / (1 - q[d]), p)
        p_falha = np.clip(np.nan_to_num(p_falha, nan=1.0), p, 1 - 1e-6)
        dz_falha[d] = np.where(aus, _logit(p_falha) - z0, 0.0)
    valor_atual = np.minimum(av["ev_defesa"], av["ev_acordo"])
    ev_instruir = c.custo_recuperar_subsidio * ausentes + (c.fator_atraso(pol.faixas.prazo_instrucao_dias) - 1) * av["ev_defesa"]
    for achados in product((1, 0), repeat=len(DOCS_INSTRUIR)):
        prob = np.ones(len(df))
        z = z0.copy()
        for d, a in zip(DOCS_INSTRUIR, achados, strict=True):
            prob *= q[d] if a else 1 - q[d]
            z += dz_com[d] if a else dz_falha[d]
        if not prob.any():
            continue
        av_o = avaliar(df, eng, _sigmoide(z))
        ev_instruir += prob * np.minimum(av_o["ev_defesa"], av_o["ev_acordo"])
    evsi = valor_atual - ev_instruir
    minimo = pol.faixas.evsi_min_pct_causa * df["valor_causa"].to_numpy(dtype=float)
    instruir = (av["decisao"] == cfg.DECISAO_ACORDO) & (ausentes > 0) & (evsi > 0) & (evsi >= minimo)
    return instruir, evsi


def _sensivel(df: pd.DataFrame, eng: Engine, p: np.ndarray, p_star: np.ndarray) -> np.ndarray:
    """IC95 de Laplace por linha cruza o breakeven?"""
    m = eng.modelo
    if not m.cov:
        return np.zeros(len(df), dtype=bool)
    x_full, _ = _matriz(df)
    xd = np.c_[np.ones(len(df)), x_full.reindex(columns=m.colunas_cov[1:], fill_value=0.0).to_numpy()]
    sd = np.sqrt(np.maximum(np.einsum("ij,jk,ik->i", xd, np.asarray(m.cov), xd), 0.0))
    z = _logit(p)
    lo, hi = _sigmoide(z - cfg.Z_IC95 * sd), _sigmoide(z + cfg.Z_IC95 * sd)
    return (lo < p_star) & (p_star < hi)


def pontuar_base(base: pd.DataFrame, eng: Engine) -> pd.DataFrame:
    """Adiciona p OOF, EV, escada, decisão binária, custo real, breakeven, EVSI/instruir e sensibilidade."""
    df = base.copy()
    p, fold = p_oof(base, eng)
    df["p_perda_hat"], df["fold"] = p, fold
    av = avaliar(df, eng, p)
    for k, v in av.items():
        df[k] = v
    df["cond_esperada_se_perde"] = df["ratio_media"] * df["valor_causa"]
    df["custo_real_defesa"] = custo_real(df, eng.politica.custos)
    df["instruir"], df["evsi"] = _instruir(df, eng, p, av)
    df["decisao_sensivel"] = _sensivel(df, eng, p, av["p_breakeven"])
    return df


# ---------------------------------------------------------------- custos sob políticas e baselines

def custo_politica(df: pd.DataFrame, eng: Engine, taxa_aceite: float | None = None, mult_oferta: float = 1.0) -> pd.Series:
    """Custo por caso sob a política. taxa_aceite=None usa a curva; senão fixa a taxa (sensibilidade)."""
    c = eng.politica.custos
    oferta = df["alvo"] * mult_oferta
    a = df["p_aceite_alvo"] if taxa_aceite is None else pd.Series(taxa_aceite, index=df.index)
    acordo = a * oferta + (1 - a) * df["custo_real_defesa"] + c.custo_escritorio_acordo
    return pd.Series(np.where(df["decisao"] == cfg.DECISAO_ACORDO, acordo, df["custo_real_defesa"]), index=df.index)


def _custo_acordo_fixo(df: pd.DataFrame, eng: Engine, mask: np.ndarray, frac: float, aceite: float) -> np.ndarray:
    c = eng.politica.custos
    real_def = df["custo_real_defesa"].to_numpy(dtype=float)
    real_aco = cst.ev_acordo(frac * df["valor_causa"].to_numpy(dtype=float), aceite, real_def, c)
    return np.where(mask, real_aco, real_def)


def _linha(nome: str, custo: np.ndarray, acordo: np.ndarray, total_def: float) -> dict:
    cst_total = float(np.sum(custo))
    return {"nome": nome, "custo": cst_total, "economia": total_def - cst_total,
            "economia_pct": (total_def - cst_total) / total_def if total_def else 0.0,
            "share_acordo": float(np.mean(acordo))}


def baselines(df: pd.DataFrame, eng: Engine) -> dict:
    """Tabela do slide: o que aconteceu, heurísticas, limiar fixo, política e oráculo."""
    pol, cmp = eng.politica, eng.politica.comparacao
    real_def = df["custo_real_defesa"].to_numpy(dtype=float)
    total_def = float(real_def.sum())
    p = df["p_perda_hat"].to_numpy(dtype=float)
    n = len(df)
    tudo = np.ones(n, dtype=bool)
    sem_contrato = (df["contrato"] == 0).to_numpy()
    sem_ambos = sem_contrato & (df["extrato"] == 0).to_numpy()
    limiar = p > LIMIAR_UFMG
    politica_acordo = (df["decisao"] == cfg.DECISAO_ACORDO).to_numpy()
    oraculo = avaliar(df, eng, df["perda"].to_numpy(dtype=float))
    oraculo_acordo = oraculo["decisao"] == cfg.DECISAO_ACORDO
    oraculo_custo = np.where(oraculo_acordo, cst.ev_acordo(oraculo["alvo"], oraculo["p_aceite_alvo"], real_def, pol.custos), real_def)
    linhas = [
        _linha("Defender tudo (o que aconteceu)", real_def, ~tudo, total_def),
        _linha(f"Acordar tudo a {cmp.oferta_pct_causa:.0%} do VC (aceite {cmp.taxa_aceite:.0%})",
               _custo_acordo_fixo(df, eng, tudo, cmp.oferta_pct_causa, cmp.taxa_aceite), tudo, total_def),
        _linha("Heurística: sem contrato → acordo", _custo_acordo_fixo(df, eng, sem_contrato, cmp.oferta_pct_causa, cmp.taxa_aceite),
               sem_contrato, total_def),
        _linha("Heurística: sem contrato e sem extrato → acordo",
               _custo_acordo_fixo(df, eng, sem_ambos, cmp.oferta_pct_causa, cmp.taxa_aceite), sem_ambos, total_def),
        _linha(f"Limiar fixo p_perda > {LIMIAR_UFMG:.2f} (3 grupos da UFMG), oferta {cmp.oferta_pct_causa:.0%}",
               _custo_acordo_fixo(df, eng, limiar, cmp.oferta_pct_causa, cmp.taxa_aceite), limiar, total_def),
        _linha(f"Política EV (p OOF, escada, aceite fixo {cmp.taxa_aceite:.0%})",
               custo_politica(df, eng, cmp.taxa_aceite).to_numpy(), politica_acordo, total_def),
        _linha("Política EV (p OOF, escada + curva de aceite)", custo_politica(df, eng).to_numpy(), politica_acordo, total_def),
        _linha("Oráculo: resultado conhecido, mesma escada (teto teórico)", oraculo_custo, oraculo_acordo, total_def),
    ]
    ganho_max = total_def - float(oraculo_custo.sum())
    for linha in linhas:
        linha["captura_do_ganho_maximo"] = linha["economia"] / ganho_max if ganho_max else 0.0
    return {"linhas": linhas, "ganho_maximo": ganho_max}


def banda(df: pd.DataFrame, eng: Engine) -> dict:
    """Variação do headline: economia % por fold (média ± sd) e bootstrap por caso."""
    custo = custo_politica(df, eng).to_numpy()
    real = df["custo_real_defesa"].to_numpy(dtype=float)
    folds = df["fold"].to_numpy()
    por_fold = [float(1 - custo[folds == k].sum() / real[folds == k].sum()) for k in sorted(set(folds)) if k >= 0]
    rng = np.random.default_rng(cfg.SEMENTE)
    n = len(df)
    bs = []
    for _ in range(N_BOOTSTRAP):
        i = rng.integers(0, n, n)
        bs.append(float(1 - custo[i].sum() / real[i].sum()))
    return {"economia_pct_por_fold": por_fold, "media": float(np.mean(por_fold)) if por_fold else None,
            "sd": float(np.std(por_fold, ddof=1)) if len(por_fold) > 1 else None,
            "bootstrap_ic95": [float(np.quantile(bs, .025)), float(np.quantile(bs, .975))], "n_bootstrap": N_BOOTSTRAP}


def avaliar_politica(df: pd.DataFrame, eng: Engine, custos: Custos | None = None, s50: float | None = None) -> dict:
    """Política completa (EV + faixas + curva de aceite) sob custos e/ou âncora de aceite alternativos."""
    c = custos or eng.politica.custos
    p = df["p_perda_hat"].to_numpy(dtype=float)
    av = avaliar(df, eng, p, c, s50)
    real_def = custo_real(df, c)
    acordo = av["decisao"] == cfg.DECISAO_ACORDO
    custo = np.where(acordo, cst.ev_acordo(av["alvo"], av["p_aceite_alvo"], real_def, c), real_def)
    total_def = float(real_def.sum())
    return {"custo_defender_tudo": total_def, "custo_politica": float(custo.sum()),
            "economia": total_def - float(custo.sum()), "economia_pct": 1 - float(custo.sum()) / total_def,
            "share_acordo": float(acordo.mean()), "p_breakeven_medio": float(av["p_breakeven"].mean()),
            "fator_tempo": c.fator_tempo}


def sensibilidade_custos(df: pd.DataFrame, eng: Engine) -> list[dict]:
    c = eng.politica.custos
    cenarios = [
        ("Base (vara: sucumbência 15%, custas 2%, 18 meses)", c),
        ("Escritório × 0,5", c.com(custo_escritorio_defesa=c.custo_escritorio_defesa * 0.5)),
        ("Escritório × 1,5", c.com(custo_escritorio_defesa=c.custo_escritorio_defesa * 1.5)),
        ("Sucumbência 10%", c.com(honorarios_sucumbencia_pct=0.10)),
        ("Sucumbência 20%", c.com(honorarios_sucumbencia_pct=0.20)),
        ("Tempo 10 meses (fator 1,10)", c.com(prazo_medio_meses=10)),
        ("Tempo 22 meses (fator 1,25)", c.com(prazo_medio_meses=22)),
        ("Sem custas", c.com(custas_pct_valor_causa=0.0)),
    ]
    for nome in eng.politica.cenarios:
        cenarios.append((f"Cenário {nome.upper()} (Lei 9.099: sem custas nem sucumbência em 1º grau, 9 meses)" if nome == "jec"
                         else f"Cenário {nome}", eng.politica.custos_cenario(nome)))
    return [{"cenario": nome, **avaliar_politica(df, eng, custos)} for nome, custos in cenarios]


def sensibilidade_s50(df: pd.DataFrame, eng: Engine) -> list[dict]:
    return [{"s50": s, **avaliar_politica(df, eng, None, s)} for s in S50_SENSIBILIDADE]


def sensibilidade_aceite(df: pd.DataFrame, eng: Engine, total_def: float) -> list[dict]:
    sens = []
    for ta in ACEITES_SENSIBILIDADE:
        for mult in MULT_OFERTA_SENSIBILIDADE:
            custo = float(custo_politica(df, eng, ta, mult).sum())
            sens.append({"taxa_aceite": "curva" if ta is None else ta, "mult_oferta": mult, "custo": custo,
                         "economia": total_def - custo, "economia_pct": (total_def - custo) / total_def})
    return sens


def resumo_instruir(df: pd.DataFrame, eng: Engine) -> dict:
    p = df["p_perda_hat"].to_numpy(dtype=float)
    av = {k: df[k].to_numpy() for k in ("ev_defesa", "ev_acordo", "decisao")}
    por_q = []
    for m in MULT_Q:
        inst, evsi = _instruir(df, eng, p, av, m)
        por_q.append({"mult_q": m, "n_instruir": int(inst.sum()), "share_instruir": float(inst.mean()),
                      "evsi_total": float(evsi[inst].sum()), "evsi_medio": float(evsi[inst].mean()) if inst.any() else 0.0})
    acordos = (df["decisao"] == cfg.DECISAO_ACORDO).to_numpy()
    return {"docs_avaliados": list(DOCS_INSTRUIR), "n_instruir": int(df["instruir"].sum()),
            "share_instruir": float(df["instruir"].mean()),
            "share_dos_acordos": float(df.loc[acordos, "instruir"].mean()) if acordos.any() else 0.0,
            "evsi_total": float(df.loc[df["instruir"], "evsi"].sum()), "por_mult_q": por_q}


def por_uf(df: pd.DataFrame, eng: Engine) -> list[dict]:
    custo = custo_politica(df, eng)
    g = pd.DataFrame({"uf": df["uf"], "acordo": df["decisao"] == cfg.DECISAO_ACORDO, "p_breakeven": df["p_breakeven"],
                      "ratio": df["ratio_media"], "perda": df["perda"], "real": df["custo_real_defesa"], "politica": custo})
    agg = g.groupby("uf").agg(n=("acordo", "size"), share_acordo=("acordo", "mean"), p_breakeven=("p_breakeven", "mean"),
                              ratio_media=("ratio", "mean"), perda_real=("perda", "mean"), defender_tudo=("real", "sum"),
                              politica=("politica", "sum"))
    agg["economia_pct"] = 1 - agg["politica"] / agg["defender_tudo"]
    return agg.reset_index().sort_values("economia_pct", ascending=False).to_dict(orient="records")


def resumo(df: pd.DataFrame, eng: Engine) -> dict:
    c = eng.politica.custos
    n = len(df)
    total_cond = float(df["valor_condenacao"].sum())
    total_defender_tudo = float(df["custo_real_defesa"].sum())
    a_all = df["p_aceite_alvo"]
    acordar_tudo = float((a_all * df["alvo"] + (1 - a_all) * df["custo_real_defesa"] + c.custo_escritorio_acordo).sum())
    politica = float(custo_politica(df, eng).sum())
    por_faixa = (df.groupby("faixa").agg(n=("numero", "size"), share=("numero", lambda s: len(s) / n),
                                          p_perda_prevista=("p_perda_hat", "mean"), perda_real=("perda", "mean"),
                                          condenacao_real=("valor_condenacao", "sum"),
                                          custo_real_defesa=("custo_real_defesa", "sum"))
                 .reset_index().to_dict(orient="records"))
    # valor de recuperar cada doc preditivo ausente (ganho se encontrar; limite superior do EVSI)
    voi = {}
    for d in cfg.DOCS_PREDITIVOS:
        sem = df[df[d] == 0]
        if sem.empty:
            continue
        df2 = sem.copy()
        df2[d] = 1
        ev2 = cst.ev_defesa(eng.modelo.p_perda_lote(df2), sem["custo_se_perde"].to_numpy(), c)
        ganho = sem["ev_defesa"].to_numpy() - ev2
        voi[d] = {"casos_sem": int(len(sem)), "ganho_total": float(ganho.sum()), "ganho_por_caso": float(ganho.mean())}
    efeito_docs = {d: {"perda_com": float(df.loc[df[d] == 1, "perda"].mean()), "perda_sem": float(df.loc[df[d] == 0, "perda"].mean())}
                   for d in cfg.DOCS}
    p_star = df["p_breakeven"]
    return {
        "n_casos": n, "base_real": bool(n >= 50000), "p_out_of_fold": bool((df["fold"] >= 0).any()),
        "n_acordos_historicos": int(df["acordo"].sum()) if "acordo" in df.columns else 0,
        "condenacao_total": total_cond, "condenacao_por_caso": total_cond / n,
        "custo_defender_tudo": total_defender_tudo, "custo_acordar_tudo": acordar_tudo,
        "custo_politica_curva": politica, "economia_politica_curva": total_defender_tudo - politica,
        "economia_pct_curva": (total_defender_tudo - politica) / total_defender_tudo,
        "share_acordo": float((df["decisao"] == cfg.DECISAO_ACORDO).mean()),
        "baselines": baselines(df, eng), "banda": banda(df, eng),
        "breakeven": {"medio": float(p_star.mean()), "p05": float(p_star.quantile(.05)), "p95": float(p_star.quantile(.95)),
                      "share_sensiveis": float(df["decisao_sensivel"].mean())},
        "sensibilidade": sensibilidade_aceite(df, eng, total_defender_tudo),
        "sensibilidade_custos": sensibilidade_custos(df, eng), "sensibilidade_s50": sensibilidade_s50(df, eng),
        "instruir": resumo_instruir(df, eng), "por_uf": por_uf(df, eng),
        "por_faixa": por_faixa, "voi": voi, "efeito_docs": efeito_docs,
        "metricas_modelo": eng.modelo.metricas, "calibracao": eng.modelo.calibracao,
        "politica_versao": eng.politica.versao, "modelo_versao": eng.modelo.versao,
        "premissas": eng.politica.model_dump(),
    }


__all__ = ["pontuar_base", "custo_politica", "resumo", "baselines", "avaliar", "p_aceite"]
