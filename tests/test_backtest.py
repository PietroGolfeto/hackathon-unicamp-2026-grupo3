from __future__ import annotations

from enteros import config as cfg
from enteros.backtest.replay import custo_politica, pontuar_base, resumo
from enteros.data.load import carregar_base, enriquecer, _ler_csv


def _base_pequena():
    base = carregar_base() if cfg.ARQ_RAW_XLSX.exists() else enriquecer(_ler_csv(cfg.ARQ_SINTETICOS))
    return base.sample(min(len(base), 5000), random_state=cfg.SEMENTE)


def test_replay_consistente(engine):
    df = pontuar_base(_base_pequena(), engine)
    assert df["decisao"].isin([cfg.DECISAO_ACORDO, cfg.DECISAO_DEFESA]).all()
    assert (df["alvo"] <= df["valor_causa"] * engine.politica.oferta.teto_pct_causa + 1e-6).all()
    # quem foi recomendado a acordo tem custo real de defesa maior em média do que quem foi a defesa
    assert df.loc[df["decisao"] == cfg.DECISAO_ACORDO, "custo_real_defesa"].mean() > \
        df.loc[df["decisao"] == cfg.DECISAO_DEFESA, "custo_real_defesa"].mean()


def test_resumo_tem_baselines_e_economia_positiva(engine):
    df = pontuar_base(_base_pequena(), engine)
    res = resumo(df, engine)
    assert res["custo_defender_tudo"] > 0
    assert res["economia_politica_curva"] > 0
    assert 0 < res["share_acordo"] < 1
    # ofertar mais caro economiza menos
    s = {(x["taxa_aceite"], x["mult_oferta"]): x["economia"] for x in res["sensibilidade"]}
    assert s[(0.7, 0.8)] > s[(0.7, 1.2)]
    assert set(res["voi"]) <= set(cfg.DOCS_PREDITIVOS)


def test_custo_politica_defesa_igual_custo_real(engine):
    df = pontuar_base(_base_pequena(), engine)
    custo = custo_politica(df, engine)
    defesa = df["decisao"] == cfg.DECISAO_DEFESA
    assert (custo[defesa] == df.loc[defesa, "custo_real_defesa"]).all()


def test_baselines_ordenados_e_banda(engine):
    df = pontuar_base(carregar_base(), engine)
    res = resumo(df, engine)
    custos = {b["nome"].split(" ")[0]: b["custo"] for b in res["baselines"]["linhas"]}
    oraculo = next(b for b in res["baselines"]["linhas"] if b["nome"].startswith("Oráculo"))
    politica = next(b for b in res["baselines"]["linhas"] if "curva de aceite" in b["nome"])
    defender = next(b for b in res["baselines"]["linhas"] if b["nome"].startswith("Defender"))
    assert oraculo["custo"] <= politica["custo"] <= defender["custo"]
    assert 0 < politica["captura_do_ganho_maximo"] <= 1
    assert res["p_out_of_fold"] is True and (df["fold"] >= 0).sum() > 0
    assert 0 < res["breakeven"]["medio"] < 1
    assert set(df["decisao"]) <= {cfg.DECISAO_ACORDO, cfg.DECISAO_DEFESA}  # replay continua binário
    assert df["instruir"].dtype == bool and not df.loc[df["decisao"] == cfg.DECISAO_DEFESA, "instruir"].any()
    assert {"jec"} <= {c["cenario"].split(" ")[1].lower() for c in res["sensibilidade_custos"] if c["cenario"].startswith("Cenário")}
    assert len(res["por_uf"]) >= 1 and custos

