from datetime import UTC, datetime

import numpy as np

from core.caso import CasoFeatures, Subsidios
from core.modelo import Scores
from core.politica import PoliticaParams, aplicar, calcular, custos_reais

PRM = PoliticaParams()
TODOS = Subsidios(contrato=True, extrato=True, comprovante_credito=True, dossie=True,
                  demonstrativo_divida=True, laudo_referenciado=True)


def scores(p: float, causa: float, p80: float | None = None) -> Scores:
    return Scores(
        numero="0000001-00.2025.8.13.0001", modelo_versao="teste", origem="stub",
        p_exito_defesa=p, condenacao_p20=0.55 * causa, condenacao_p50=0.74 * causa,
        condenacao_p80=p80 if p80 is not None else 0.86 * causa, gerado_em=datetime(2026, 9, 12, tzinfo=UTC),
    )


def caso(causa: float, subs: Subsidios | None = None, sinais: dict | None = None) -> CasoFeatures:
    return CasoFeatures(numero="0000001-00.2025.8.13.0001", uf="MG", sub_assunto="Golpe",
                        valor_causa=causa, subsidios=subs or Subsidios(), sinais=sinais or {})


def test_sem_subsidios_recomenda_acordo():
    rec = aplicar(scores(0.03, 15000), caso(15000), PRM, politica_id=1)
    assert rec.tipo == "acordo"
    assert rec.regra == "acordo_forte"
    assert rec.valor_sugerido is not None and rec.valor_min < rec.valor_sugerido < rec.valor_max
    assert len(rec.motivos) == 3 and all(m for m in rec.motivos)
    assert "nenhum dos seis subsídios" in rec.motivos[1]


def test_seis_subsidios_recomenda_defesa():
    rec = aplicar(scores(0.96, 15000), caso(15000, TODOS), PRM, politica_id=1)
    assert rec.tipo == "defesa"
    assert rec.regra == "defesa_forte"
    assert rec.valor_sugerido is None and rec.valor_min is None
    assert "seis subsídios" in rec.motivos[1]


def test_sinal_forca_acordo_mesmo_com_defesa_forte():
    rec = aplicar(scores(0.96, 15000), caso(15000, TODOS, {"CREDITO_CONTA_TERCEIRO": True}),
                  PRM, politica_id=1)
    assert rec.tipo == "acordo"
    assert rec.regra == "sinal"
    assert rec.sinais_acionados == ["CREDITO_CONTA_TERCEIRO"]
    assert "força acordo" in rec.motivos[0]


def test_sinal_fora_da_lista_nao_forca():
    rec = aplicar(scores(0.96, 15000), caso(15000, TODOS, {"IDOSO": True}), PRM, politica_id=1)
    assert rec.tipo == "defesa"


def test_oferta_no_piso():
    # q = 0.16, p50 = 11.100 -> bruta 0,8·0,16·11.100 = 1.420,8 -> 1.400; piso 10% = 1.500
    rec = aplicar(scores(0.84, 15000), caso(15000), PoliticaParams(limiar_acordo_forte=0.85),
                  politica_id=1)
    assert rec.tipo == "acordo"
    assert rec.valor_sugerido == 1500
    assert "piso" in rec.motivos[2]


def test_oferta_no_teto_pelo_valor_da_causa():
    prm = PoliticaParams(teto_oferta_pct_causa=0.40)
    rec = aplicar(scores(0.31, 10000), caso(10000), prm, politica_id=1)
    assert rec.tipo == "acordo"
    assert rec.valor_sugerido == 4000  # 40% de 10.000; bruta seria 4.100
    assert "teto" in rec.motivos[2]


def test_oferta_no_teto_pela_condenacao_p80():
    rec = aplicar(scores(0.31, 10000, p80=3000), caso(10000), PRM, politica_id=1)
    assert rec.valor_sugerido == 3000


def test_zona_cinzenta_decide_por_custo():
    prm = PoliticaParams(taxa_aceite_esperada=1.0)
    rec = aplicar(scores(0.5, 15000), caso(15000), prm, politica_id=1)
    assert rec.regra == "custo"
    assert rec.tipo == "acordo"
    assert rec.economia_esperada > 0
    prm_caro = PoliticaParams(taxa_aceite_esperada=0.0)
    rec2 = aplicar(scores(0.5, 15000), caso(15000), prm_caro, politica_id=1)
    assert rec2.tipo == "defesa"  # com ninguém aceitando, acordo só adiciona custo operacional


def test_vetorizado_bate_com_escalar():
    ps = np.array([0.03, 0.5, 0.96])
    causas = np.array([15000.0, 15000.0, 15000.0])
    lote = calcular(ps, 0.55 * causas, 0.74 * causas, 0.86 * causas, causas, PRM)
    for i, p in enumerate(ps):
        um = calcular(p, 0.55 * 15000, 0.74 * 15000, 0.86 * 15000, 15000.0, PRM)
        assert bool(lote["acordo"][i]) == bool(um["acordo"])
        assert lote["oferta"][i] == float(um["oferta"])
        assert np.isclose(lote["custo_defesa"][i], float(um["custo_defesa"]))
    assert list(lote["acordo"]) == [True, True, False]
    assert list(lote["regra"]) == ["acordo_forte", "custo", "defesa_forte"]


def test_custos_reais_e_baselines():
    ps = np.array([0.03, 0.96])
    causas = np.array([10000.0, 10000.0])
    r = custos_reais(ps, 5500, 7400, 8600, causas, perdeu=[True, False],
                     valor_condenacao=[7400.0, np.nan], prm=PRM)
    # perdeu: 1.500 + 1.000 + 7.400·1,1 = 10.640; ganhou: 1.500 + 1.000
    assert np.allclose(r["custo_defesa_real"], [10640.0, 2500.0])
    assert r["custo_politica"][0] == r["custo_acordo_real"][0]  # acordo
    assert r["custo_politica"][1] == r["custo_defesa_real"][1]  # defesa
    assert r["custo_politica"].sum() < r["custo_defesa_real"].sum()


def test_params_incoerentes_falham():
    import pytest

    with pytest.raises(ValueError):
        PoliticaParams(limiar_acordo_forte=0.9, limiar_defesa_forte=0.5)
    with pytest.raises(ValueError):
        PoliticaParams(arredondamento=0)
