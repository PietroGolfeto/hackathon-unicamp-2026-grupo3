import pytest

from core.cnj import TJ_UF, normalizar, uf_do_numero, validar

# exemplos reais da base da Enter e dos processos exemplo da edição anterior
CASOS = [
    ("1764352-89.2025.8.06.1818", "CE"),
    ("5638325-36.2025.8.17.4124", "PE"),
    ("1037491-89.2025.8.18.1658", "PI"),
    ("9547931-23.2025.8.04.4188", "AM"),
    ("0654321-09.2024.8.04.0001", "AM"),
    ("0801234-56.2024.8.10.0001", "MA"),
]


@pytest.mark.parametrize(("numero", "uf"), CASOS)
def test_uf_do_numero(numero, uf):
    assert uf_do_numero(numero) == uf


def test_tabela_cobre_os_27_tribunais_estaduais():
    assert len(TJ_UF) == 27
    assert len(set(TJ_UF.values())) == 27


def test_normalizar_aceita_sem_pontuacao():
    assert normalizar("17643528920258061818") == "1764352-89.2025.8.06.1818"
    assert normalizar(" 1764352-89.2025.8.06.1818 ") == "1764352-89.2025.8.06.1818"


def test_invalidos():
    assert not validar("123")
    assert not validar(None)
    assert uf_do_numero("abc") is None


def test_outro_segmento_de_justica_nao_tem_uf():
    assert uf_do_numero("0000001-00.2024.4.03.6100") is None  # Justiça Federal, TRF3
