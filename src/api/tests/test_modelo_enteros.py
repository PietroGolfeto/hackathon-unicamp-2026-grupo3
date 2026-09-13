"""Adapter do engine de P1 como ModeloScores. Não precisa de banco."""

import pandas as pd
import pytest
from core.caso import CasoFeatures, Subsidios

modelo_enteros = pytest.importorskip("app.modelo_enteros")

TODOS = Subsidios(contrato=True, extrato=True, comprovante_credito=True, dossie=True,
                  demonstrativo_divida=True, laudo_referenciado=True)


@pytest.fixture(scope="module")
def modelo():
    return modelo_enteros.ModeloEnteros()


def test_scores_seguem_o_contrato_e_a_direcao(modelo):
    forte = modelo.score(CasoFeatures(numero="a", uf="MA", sub_assunto="Genérico", valor_causa=20000, subsidios=TODOS))
    fraco = modelo.score(CasoFeatures(numero="b", uf="AM", sub_assunto="Golpe", valor_causa=25000))
    assert forte.origem == "modelo" and forte.modelo_versao.startswith("enteros-")
    assert forte.p_exito_defesa > 0.9
    assert fraco.p_exito_defesa < 0.2
    assert 0 < fraco.condenacao_p20 <= fraco.condenacao_p50 <= fraco.condenacao_p80 <= 25000
    assert len(forte.contribuicoes) <= 5
    contrato = next(c for c in fraco.contribuicoes if c.feature == "Contrato")
    assert contrato.contribuicao < 0  # ausente derruba o êxito


def test_uf_e_sub_assunto_desconhecidos_nao_quebram(modelo):
    s = modelo.score(CasoFeatures(numero="c", uf="ZZ", sub_assunto=None, valor_causa=1000))
    assert 0 <= s.p_exito_defesa <= 1


def test_lote_bate_com_a_direcao_e_o_tamanho(modelo):
    df = pd.DataFrame({
        "uf": ["MG", "MG"], "sub_assunto": ["Golpe", "Golpe"], "valor_causa": [10000.0, 10000.0],
        "contrato": [False, True], "extrato": [False, True], "comprovante_credito": [False, True],
        "dossie": [False, True], "demonstrativo_divida": [False, True], "laudo_referenciado": [False, True],
    })
    p = modelo.p_exito_lote(df)
    assert p.shape == (2,) and p[0] < p[1]
    q = modelo.quantis_lote(df)
    assert (q["p20"] <= q["p50"]).all() and (q["p50"] <= q["p80"]).all()


def test_info_traz_metricas_e_calibracao_em_termos_de_exito(modelo):
    info = modelo.info()
    assert info.n_treino > 0 and "auc_oof" in info.metricas
    assert len(info.calibracao) >= 5
    assert all(0 <= b.p_min <= b.p_max <= 1 for b in info.calibracao)
    assert info.importancias["contrato"] > info.importancias["dossie"]


def test_instrucao_de_subsidios_vem_do_engine(modelo):
    """Faltando só o extrato, o caso fica na zona em que compensa pedi-lo antes de acordar."""
    sem_extrato = Subsidios(contrato=True, comprovante_credito=True, dossie=True,
                            demonstrativo_divida=True, laudo_referenciado=True)
    meio = modelo.score(CasoFeatures(numero="c", uf="MA", sub_assunto="Golpe",
                                     valor_causa=20000, subsidios=sem_extrato))
    assert meio.instruir_recomendado is True
    assert meio.docs_a_solicitar == ["extrato"]
    assert meio.evsi_por_doc.get("extrato", 0) > 0

    completo = modelo.score(CasoFeatures(numero="d", uf="MA", sub_assunto="Golpe",
                                         valor_causa=20000, subsidios=TODOS))
    assert completo.instruir_recomendado is False and completo.docs_a_solicitar == []
