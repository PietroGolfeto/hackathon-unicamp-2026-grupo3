from __future__ import annotations

import pytest

from enteros import config as cfg
from enteros.schemas import CaseFeatures, DocsStatus


def test_caso_01_defesa(engine, caso_01):
    r = engine.recomendar(caso_01)
    assert r.decisao == cfg.DECISAO_DEFESA
    assert r.faixa == cfg.FAIXA_VERDE
    assert r.p_perda < 0.02
    assert r.escada is None
    assert any("Contradições" in m for m in r.motivos)


def test_caso_02_acordo_com_escada(engine, caso_02):
    r = engine.recomendar(caso_02)
    assert r.decisao == cfg.DECISAO_ACORDO
    assert r.faixa == cfg.FAIXA_VERMELHA
    assert r.p_perda > 0.90
    assert r.escada is not None
    assert r.escada.piso <= r.escada.abertura <= r.escada.alvo <= r.escada.teto
    assert r.escada.teto < r.ev_defesa
    assert r.ev_acordo < r.ev_defesa
    assert r.decomposicao.devolucao_parcelas == pytest.approx(8 * 180.0)
    assert r.decomposicao.dano_moral == pytest.approx(r.escada.alvo - 8 * 180.0)
    assert "SINAL_FORCA_ACORDO:CREDITO_CONTA_TERCEIRO" in r.regras_acionadas


def test_caso_02_sem_sinais_vira_instruir(engine, caso_02):
    caso = caso_02.model_copy(update={"conta_deposito_titular_autor": None, "liveness_presente": None, "red_flags": []})
    r = engine.recomendar(caso)
    assert r.decisao == cfg.DECISAO_INSTRUIR
    assert r.decisao_se_nao_recuperar == cfg.DECISAO_ACORDO
    assert set(r.docs_a_solicitar) == {"contrato", "extrato"}
    assert r.voi_por_doc["contrato"] > 0


def test_mais_documentos_nunca_aumenta_risco(engine):
    base = CaseFeatures(uf="SP", sub_assunto=cfg.SUB_GOLPE, valor_causa=15000.0)
    p_anterior = 1.0
    docs: dict[str, str] = {}
    for d in cfg.DOCS_PREDITIVOS:
        docs[d] = cfg.STATUS_PRESENTE
        p = engine.recomendar(base.model_copy(update={"docs": DocsStatus(**docs)})).p_perda
        assert p <= p_anterior + 1e-9
        p_anterior = p


def test_inconsistente_vale_ausente(engine):
    presente = DocsStatus(contrato=cfg.STATUS_PRESENTE, extrato=cfg.STATUS_PRESENTE)
    inconsistente = DocsStatus(contrato=cfg.STATUS_PRESENTE, extrato=cfg.STATUS_INCONSISTENTE)
    ausente = DocsStatus(contrato=cfg.STATUS_PRESENTE)
    f = lambda d: engine.recomendar(CaseFeatures(uf="RJ", sub_assunto=cfg.SUB_GOLPE, valor_causa=12000.0, docs=d))
    assert f(inconsistente).p_perda == pytest.approx(f(ausente).p_perda)
    assert f(inconsistente).p_perda > f(presente).p_perda


def test_conta_terceiro_rebaixa_extrato_e_forca_acordo(engine):
    docs = DocsStatus(contrato=cfg.STATUS_PRESENTE, extrato=cfg.STATUS_PRESENTE, comprovante=cfg.STATUS_PRESENTE)
    ok = engine.recomendar(CaseFeatures(uf="MG", sub_assunto=cfg.SUB_GOLPE, valor_causa=15000.0, docs=docs))
    terceiro = engine.recomendar(CaseFeatures(uf="MG", sub_assunto=cfg.SUB_GOLPE, valor_causa=15000.0, docs=docs,
                                              conta_deposito_titular_autor=False))
    assert ok.decisao == cfg.DECISAO_DEFESA
    assert terceiro.decisao == cfg.DECISAO_ACORDO
    assert "EXTRATO_REBAIXADO_CONTA_TERCEIRO" in terceiro.regras_acionadas
    assert terceiro.p_perda > ok.p_perda


def test_uf_invalida():
    with pytest.raises(ValueError):
        CaseFeatures(uf="XX", valor_causa=1000.0)


def test_contribuicoes_explicam_direcao(engine, caso_02):
    r = engine.recomendar(caso_02)
    nomes = {c["feature"]: c["contribuicao"] for c in r.contribuicoes}
    assert nomes["Contrato"] > 0 and nomes["Extrato"] > 0  # ausentes aumentam o risco
