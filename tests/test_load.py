from __future__ import annotations

from enteros import config as cfg
from enteros.data.load import COLUNAS_CANONICAS, _ler_csv, enriquecer


def test_sinteticos_carregam_com_schema():
    base = enriquecer(_ler_csv(cfg.ARQ_SINTETICOS))
    assert set(COLUNAS_CANONICAS) <= set(base.columns)
    assert base["numero"].is_unique
    assert set(base["sub_assunto"]) <= set(cfg.SUB_ASSUNTOS)
    assert base.loc[base["perda"] == 0, "valor_condenacao"].eq(0).all()
    assert base["ratio"].dropna().between(0.199, 1.001).all()  # arredondamento a centavos
