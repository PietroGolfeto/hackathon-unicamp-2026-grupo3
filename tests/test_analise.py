"""Análises para a demo rodam na base sintética e não alteram o modelo."""

from __future__ import annotations

from enteros import config as cfg
from enteros.analise import aceite, fronteira, severidade
from enteros.analise.comum import engine_com
from enteros.backtest.replay import pontuar_base
from enteros.data.load import _ler_csv, enriquecer


def _df(engine):
    return pontuar_base(enriquecer(_ler_csv(cfg.ARQ_SINTETICOS)), engine)


def test_engine_com_nao_muda_o_original(engine):
    e2 = engine_com(engine, limiar_verde=0.05, margem_teto=0.3)
    assert e2.politica.faixas.limiar_verde == 0.05 and e2.politica.oferta.margem_teto == 0.3
    assert engine.politica.faixas.limiar_verde != 0.05 and engine.politica.oferta.margem_teto != 0.3
    assert e2.modelo is engine.modelo


def test_fronteira_tem_pareto_e_politica_atual(engine, tmp_path):
    df = _df(engine)
    grade = {"aceite_s50": (0.30, 0.40), "teto_pct_causa": (0.70,), "margem_teto": (0.10, 0.30), "limiar_verde": (0.15,)}
    res = fronteira.analisar(df, engine, tmp_path, grade, mundos=(0.30, 0.40))
    assert res["n_configuracoes"] == 4 and len(res["pareto"]) >= 1
    assert res["atual"] is not None and res["atual"]["custo_pior"] >= res["atual"]["custo_base"] - 1e-6
    assert res["robusta"]["economia_pct_pior"] >= res["atual"]["economia_pct_pior"] - 1e-9
    assert (tmp_path / "fronteira_politica.png").exists()


def test_posterior_de_aceite_aprende_o_mundo(engine):
    df = _df(engine)
    escadas = aceite.escadas_da_base(df, engine)
    tr, post = aceite.simular(escadas, engine, s50_true=0.40, largura_true=0.06, n=600, semente=1)
    r = post.resumo()
    assert abs(r["s50_media"] - 0.40) < 0.04
    assert r["s50_ic90"][0] <= 0.40 <= r["s50_ic90"][1]
    assert tr["s50_sd"].iloc[-1] < tr["s50_sd"].iloc[0]


def test_severidade_decompoe_a_variacao_entre_ufs(tmp_path):
    base = enriquecer(_ler_csv(cfg.ARQ_SINTETICOS))
    res = severidade.analisar(base, tmp_path)
    assert len(res["por_uf"]) >= 10
    assert 0 <= res["decomposicao"]["share_var_explicada_pela_parcial"]
    assert (tmp_path / "severidade_uf.png").exists() and (tmp_path / "severidade_distribuicao.png").exists()
