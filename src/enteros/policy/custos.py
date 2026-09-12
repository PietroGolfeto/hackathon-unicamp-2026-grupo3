"""Custo total de litigar e de acordar: funções puras em numpy, compartilhadas por engine, backtest e
comparação de modelos.

Convenção: `p` é a probabilidade de perda em sentença; `ratio` é condenação ÷ valor da causa dado perda.
    EV_defesa = escritório + p·[ratio·VC·(1 + sucumbência)·fator_tempo + custas·VC + saldo]
    EV_acordo = a·(oferta + saldo) + (1 − a)·EV_defesa + operacional
    p*        = p acima do qual EV_acordo < EV_defesa (breakeven)
`saldo` é o saldo devedor baixado (receita que o banco perde se cancelar o contrato; entra nos dois ramos
porque, perdendo em juízo, o contrato também é anulado). Vale 0 quando a IA documental não informa.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from enteros.policy.params import Custos, Politica

Vetor = np.ndarray | float


def custo_se_perde(ratio: Any, valor_causa: Any, c: Custos) -> Vetor:
    """Desembolso se o banco perder: condenação corrigida + sucumbência + custas."""
    vc = np.asarray(valor_causa, dtype=float)
    cond = np.asarray(ratio, dtype=float) * vc
    return cond * (1 + c.honorarios_sucumbencia_pct) * c.fator_tempo + c.custas_pct_valor_causa * vc


def ev_defesa(p: Any, custo_perda: Any, c: Custos, saldo: Any = 0.0) -> Vetor:
    return c.custo_escritorio_defesa + np.asarray(p, dtype=float) * (np.asarray(custo_perda, dtype=float) + saldo)


def custo_real_defesa(perda: Any, condenacao: Any, valor_causa: Any, c: Custos) -> Vetor:
    """O que defender custou de fato, dado o resultado observado."""
    vc = np.asarray(valor_causa, dtype=float)
    cond = np.nan_to_num(np.asarray(condenacao, dtype=float), nan=0.0)
    return c.custo_escritorio_defesa + np.asarray(perda, dtype=float) * (
        cond * (1 + c.honorarios_sucumbencia_pct) * c.fator_tempo + c.custas_pct_valor_causa * vc
    )


def ev_acordo(oferta: Any, p_aceite: Any, ev_def: Any, c: Custos, saldo: Any = 0.0) -> Vetor:
    a = np.asarray(p_aceite, dtype=float)
    return a * (np.asarray(oferta, dtype=float) + saldo) + (1 - a) * np.asarray(ev_def, dtype=float) + c.custo_escritorio_acordo


def breakeven(oferta: Any, p_aceite: Any, custo_perda: Any, c: Custos, saldo: Any = 0.0) -> Vetor:
    """p* tal que EV_acordo(oferta) = EV_defesa. Acima dele o acordo é mais barato."""
    num = np.asarray(oferta, dtype=float) + saldo + c.custo_escritorio_acordo / np.asarray(p_aceite, dtype=float) \
        - c.custo_escritorio_defesa
    return np.clip(num / (np.asarray(custo_perda, dtype=float) + saldo), 0.0, 1.0)


def ratio_por_linha(base: pd.DataFrame, referencia: pd.DataFrame | None = None) -> np.ndarray:
    """Ratio médio de condenação por UF × sub-assunto (só sentenças perdidas), mapeado em cada linha de `base`."""
    ref = base if referencia is None else referencia
    col_perda = "perda_sentenca" if "perda_sentenca" in ref.columns else "perda"
    perdas = ref[ref[col_perda] == 1]
    medias = perdas.groupby(["uf", "sub_assunto"])["ratio"].mean()
    idx = pd.MultiIndex.from_frame(base[["uf", "sub_assunto"]])
    r = medias.reindex(idx).to_numpy(dtype=float)
    return np.where(np.isnan(r), float(perdas["ratio"].mean()), r)


def custo_regra_fixa(p: Any, base: pd.DataFrame, politica: Politica) -> dict[str, float]:
    """Custo realizado de decidir por EV com oferta fixa (política.comparacao) usando `p` como probabilidade.

    Cenário comum para comparar modelos: mesma oferta, mesmo aceite, mesmos custos; só `p` muda.
    """
    c, cmp = politica.custos, politica.comparacao
    vc = base["valor_causa"].to_numpy(dtype=float)
    ratio = ratio_por_linha(base)
    ev_def = ev_defesa(p, custo_se_perde(ratio, vc, c), c)
    oferta = cmp.oferta_pct_causa * vc
    acordo = ev_acordo(oferta, cmp.taxa_aceite, ev_def, c) < ev_def
    real_def = custo_real_defesa(base["perda"].to_numpy(), base["valor_condenacao"].to_numpy(), vc, c)
    real_aco = ev_acordo(oferta, cmp.taxa_aceite, real_def, c)
    total = np.where(acordo, real_aco, real_def)
    return {
        "custo_total": float(total.sum()),
        "custo_defender_tudo": float(real_def.sum()),
        "share_acordo": float(np.mean(acordo)),
    }
