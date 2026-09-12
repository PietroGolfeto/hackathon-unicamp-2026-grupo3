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


# ---------- v2: três ações, breakeven, EVSI e saldo ----------

def _caso(uf: str, sub: str, vc: float = 15000.0, **docs: str) -> CaseFeatures:
    return CaseFeatures(uf=uf, sub_assunto=sub, valor_causa=vc, docs=DocsStatus(**docs))


def test_caso_02_instrui_pelo_conjunto_contrato_extrato(engine, caso_02):
    r = engine.recomendar(caso_02.model_copy(update={"conta_deposito_titular_autor": None, "liveness_presente": None}))
    assert r.decisao == cfg.DECISAO_INSTRUIR
    assert set(r.instrucao["docs"]) == {"contrato", "extrato"}
    assert r.instrucao["evsi"] > 0 and r.ev_instruir < r.ev_acordo < r.ev_defesa
    # cada documento sozinho vale pouco (o caso continua acordo); o par vira a decisão
    assert r.instrucao["evsi"] > max(a["evsi"] for a in r.analise_subsidios.values())
    assert 0 < r.instrucao["p_todos_encontrados"] < 1


def test_p_falha_fecha_a_probabilidade_total(engine):
    r = engine.recomendar(_caso("MA", cfg.SUB_GOLPE, contrato=cfg.STATUS_PRESENTE, comprovante=cfg.STATUS_PRESENTE))
    a = r.analise_subsidios["demonstrativo"]
    assert a["p_falha"] < 1.0  # caso não clipado
    assert a["q"] * a["p_com"] + (1 - a["q"]) * a["p_falha"] == pytest.approx(r.p_perda, abs=2e-3)
    assert a["p_com"] < r.p_perda < a["p_falha"]


def test_breakeven_e_o_ponto_de_indiferenca(engine):
    from enteros.policy import custos as cst

    caso = _caso("SP", cfg.SUB_GOLPE, extrato=cfg.STATUS_PRESENTE, comprovante=cfg.STATUS_PRESENTE)
    r = engine.recomendar(caso)
    assert 0 < r.p_breakeven < 1
    ev_def_star, _ = engine.ev_defesa(r.p_breakeven, caso.uf, caso.sub_assunto, caso.valor_causa)
    esc = r.escada if r.escada is not None else engine.avaliar(caso, r.p_perda, 0.0).escada
    ev_aco_star = cst.ev_acordo(esc.alvo, esc.p_aceite_alvo, ev_def_star, engine.politica.custos)
    assert ev_aco_star == pytest.approx(ev_def_star, rel=1e-3)  # p_breakeven é exportado com 4 casas


def test_saldo_devedor_entra_nos_dois_ramos(engine, caso_02):
    com = engine.recomendar(caso_02)
    sem = engine.recomendar(caso_02.model_copy(update={"saldo_devedor": None}))
    assert com.saldo_no_ev == pytest.approx(caso_02.saldo_devedor)
    assert com.ev_defesa - sem.ev_defesa == pytest.approx(com.p_perda * caso_02.saldo_devedor, rel=1e-3)
    assert com.ev_acordo > sem.ev_acordo
    assert com.escada.teto <= sem.escada.teto


def test_defesa_lista_docs_que_fortalecem_sem_atrasar(engine):
    r = engine.recomendar(_caso("SP", cfg.SUB_GOLPE, contrato=cfg.STATUS_PRESENTE, extrato=cfg.STATUS_PRESENTE,
                                comprovante=cfg.STATUS_PRESENTE))
    assert r.decisao == cfg.DECISAO_DEFESA and r.faixa == cfg.FAIXA_VERDE
    assert r.docs_a_solicitar == []  # não se adia uma defesa
    assert "demonstrativo" in r.docs_que_fortalecem
    assert "SOLICITAR_EM_PARALELO_A_DEFESA" in r.regras_acionadas
    assert r.voi_por_doc["demonstrativo"] > engine.politica.custos.custo_recuperar_subsidio


def test_intervalo_e_epistemico_e_sensibilidade_e_rara(engine, caso_01, caso_02):
    for caso in (caso_01, caso_02):
        r = engine.recomendar(caso)
        lo, hi = r.p_perda_intervalo
        assert lo <= r.p_perda <= hi and hi - lo < 0.1
        assert r.decisao_sensivel is False
