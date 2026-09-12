"""Modelo de perda v2: logística única, coeficientes nulos exportados, UF encolhida, IC de Laplace, q_doc."""

from __future__ import annotations

import pytest

from enteros import config as cfg
from enteros.data.load import _ler_csv, enriquecer
from enteros.policy.model import DOCS_NULOS, ModeloPerda


def _flags(**presentes: int) -> dict[str, int]:
    return {d: int(presentes.get(d, 0)) for d in cfg.DOCS}


TODOS = _flags(**dict.fromkeys(cfg.DOCS, 1))


def test_colunas_e_coeficientes_exportados(engine):
    m = engine.modelo
    assert len(m.colunas) == len(m.coef)
    coefs = dict(zip(m.colunas, m.coef, strict=True))
    for d in DOCS_NULOS:
        assert coefs[d] == 0.0  # dossiê e laudo: efeito nulo, mantidos para o adapter do portal
    for d in cfg.DOCS_PREDITIVOS:
        assert coefs[d] < 0  # presente protege
    assert coefs["sub_golpe"] > 0
    assert m.metricas["auc_oof"] > 0.9 and m.metricas["ece_oof"] < 0.02
    assert m.metricas["n_acordos_excluidos"] > 0
    assert m.metricas["custo_decisao_oof"] < m.metricas["custo_defender_tudo"]


def test_intervalo_laplace_contem_p_e_e_estreito(engine):
    m = engine.modelo
    for uf, flags in [("AM", _flags(comprovante=1, demonstrativo=1)), ("MA", TODOS), ("SP", _flags(contrato=1)), ("", TODOS)]:
        p = m.p_perda(cfg.SUB_GOLPE, flags, uf)
        lo, hi = m.p_perda_intervalo(cfg.SUB_GOLPE, flags, uf)
        assert lo <= p <= hi
        assert 0 < hi - lo < 0.15


def test_uf_desconhecida_e_a_uf_media(engine):
    m = engine.modelo
    flags = _flags(contrato=1, extrato=1)
    com_dados = [uf for uf, e in m.efeitos_uf.items() if e["n"] > 0]
    ps = [m.p_perda(cfg.SUB_GOLPE, flags, uf) for uf in com_dados]
    p_media = m.p_perda(cfg.SUB_GOLPE, flags, "")
    assert min(ps) < p_media < max(ps)


def test_encolhimento_puxa_ufs_para_a_media(engine):
    m = engine.modelo
    com_dados = [e for e in m.efeitos_uf.values() if e["n"] > 0]
    assert 0 < m.tau_uf < 1
    for e in com_dados:
        assert abs(e["encolhido"] - m.media_uf) <= abs(e["bruto"] - m.media_uf) + 1e-12
        assert 0 < e["fator"] < 1
    assert m.efeitos_uf["AP"]["encolhido"] > m.efeitos_uf["MA"]["encolhido"]


def test_q_doc_fica_em_zero_um_e_depende_do_padrao(engine):
    m = engine.modelo
    fraco, forte = _flags(comprovante=1, demonstrativo=1), _flags(extrato=1, comprovante=1, demonstrativo=1)
    for d in cfg.DOCS_PREDITIVOS:
        assert 0 < m.q_doc_para(d, fraco, 0.6) < 1
    assert m.q_doc_para("contrato", forte, 0.6) > m.q_doc_para("contrato", fraco, 0.6)  # com extrato, contrato é mais comum


def test_tabela_de_segmentos_e_saida_do_modelo(engine):
    m, s = engine.modelo, engine.segmentos
    flags = _flags(contrato=1, extrato=1, comprovante=1, demonstrativo=1)
    p_seg, n = s.p_perda(cfg.SUB_GENERICO, flags, "MA")
    assert n > 0
    assert p_seg == pytest.approx(m.p_perda(cfg.SUB_GENERICO, flags, "MA"), abs=1e-6)


def test_ajuste_roda_na_base_sintetica():
    base = enriquecer(_ler_csv(cfg.ARQ_SINTETICOS))
    m = ModeloPerda.ajustar(base, "logit-teste-20260912")
    assert len(m.colunas) == len(m.coef)
    assert len(m.cov) == len(m.colunas_cov) == len(m.cov[0])
    assert dict(zip(m.colunas, m.coef, strict=True))["contrato"] < 0
    assert m.versao.endswith("20260912")


def test_ratio_sem_acordos_monotono_e_por_uf(engine):
    r = engine.ratio
    assert r.global_["n"] == sum(c["n"] for c in r.por_uf_sub.values())
    assert r.global_["n"] == sum(c["n"] for c in r.por_sub.values())
    for c in [*r.por_uf_sub.values(), *r.por_sub.values(), r.global_]:
        assert 0.2 <= c["p20"] <= c["p50"] <= c["p80"] <= 1.0
        assert 0 < c["p_procedencia"] < 1
        assert c["media_parcial"] < c["media_procedencia"]
    assert r.para("MA", cfg.SUB_GENERICO)["media"] < r.para("AP", cfg.SUB_GOLPE)["media"]
    assert r.para("AM", cfg.SUB_GOLPE)["media"] > 0.75 > r.para("MA", cfg.SUB_GOLPE)["media"]
    assert set(("media", "p20", "p50", "p80", "n")) <= set(r.para("", "nan"))  # fallback do adapter


def test_comparacao_de_modelos_roda_na_base_sintetica():
    from enteros.policy.comparar import comparar, para_markdown

    base = enriquecer(_ler_csv(cfg.ARQ_SINTETICOS))
    res = comparar(base)
    nomes = [linha["modelo"] for linha in res["linhas"]]
    assert any("v2, escolhida" in n for n in nomes) and any(n.startswith("Engine v1") for n in nomes)
    assert all(0 < linha["auc_oof"] <= 1 and linha["custo_oof"] > 0 for linha in res["linhas"])
    assert res["custo_oraculo"] <= min(linha["custo_oof"] for linha in res["linhas"])
    assert "| modelo |" in para_markdown(res)
