from core.colunas import (
    FLAGS_SUBSIDIOS,
    mapear_colunas,
    normalizar_nome,
    parse_brl,
    resultado_macro_para_int,
)

CABECALHO_RESULTADOS = [
    "Número do processo", "UF", "Assunto", "Sub-assunto", "Resultado macro",
    "Resultado micro", "Valor da causa", "Valor da condenação/indenização",
]
CABECALHO_SUBSIDIOS = [
    "Número do processos", "Contrato", "Extrato", "Comprovante de crédito", "Dossiê",
    "Demonstrativo de evolução da dívida", "Laudo referenciado",
]


def test_normalizar_nome_remove_acento_caixa_e_espacos():
    assert normalizar_nome("  Número do  Processo ") == "numero do processo"
    assert normalizar_nome("Dossiê") == "dossie"


def test_mapeia_todas_as_colunas_dos_dois_csvs_da_enter():
    resultados = mapear_colunas(CABECALHO_RESULTADOS)
    subsidios = mapear_colunas(CABECALHO_SUBSIDIOS)
    assert list(resultados.values()) == [
        "numero", "uf", "assunto", "sub_assunto", "resultado_macro",
        "resultado_micro", "valor_causa", "valor_condenacao",
    ]
    assert list(subsidios.values()) == ["numero", *FLAGS_SUBSIDIOS]


def test_numero_com_e_sem_s_caem_no_mesmo_nome():
    assert mapear_colunas(["Número do processo"])["Número do processo"] == "numero"
    assert mapear_colunas(["Número do processos"])["Número do processos"] == "numero"


def test_coluna_desconhecida_e_ignorada():
    assert mapear_colunas(["Coluna qualquer"]) == {}


def test_parse_brl_formato_brasileiro():
    assert parse_brl("13.534,00") == 13534.0
    assert parse_brl("7.714,38") == 7714.38
    assert parse_brl("R$ 1.000,50") == 1000.5
    assert parse_brl("0,00") == 0.0
    assert parse_brl("999,9") == 999.9


def test_parse_brl_outros_formatos_e_vazios():
    assert parse_brl("1,234.50") == 1234.5
    assert parse_brl("1000.5") == 1000.5
    assert parse_brl(1500) == 1500.0
    assert parse_brl(None) is None
    assert parse_brl("") is None
    assert parse_brl("NaN") is None
    assert parse_brl(float("nan")) is None
    assert parse_brl("abc") is None


def test_resultado_macro():
    assert resultado_macro_para_int("Êxito") == 1
    assert resultado_macro_para_int("Não Êxito") == 0
    assert resultado_macro_para_int(1) == 1
    assert resultado_macro_para_int("Extinção") is None
