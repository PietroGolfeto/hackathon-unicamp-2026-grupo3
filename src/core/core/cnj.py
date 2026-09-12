"""Número único de processo (CNJ): NNNNNNN-DD.AAAA.J.TR.OOOO.

J = segmento da Justiça (8 = Justiça Estadual). TR identifica o tribunal; na Justiça Estadual
cada TJ corresponde a uma UF, então a UF é derivável do número sem consultar nada.
"""

from __future__ import annotations

import re

PADRAO = re.compile(r"^(\d{7})-(\d{2})\.(\d{4})\.(\d)\.(\d{2})\.(\d{4})$")
JUSTICA_ESTADUAL = "8"

# Código TR dos Tribunais de Justiça estaduais -> UF
TJ_UF: dict[str, str] = {
    "01": "AC", "02": "AL", "03": "AP", "04": "AM", "05": "BA", "06": "CE", "07": "DF",
    "08": "ES", "09": "GO", "10": "MA", "11": "MT", "12": "MS", "13": "MG", "14": "PA",
    "15": "PB", "16": "PR", "17": "PE", "18": "PI", "19": "RJ", "20": "RN", "21": "RS",
    "22": "RO", "23": "RR", "24": "SC", "25": "SE", "26": "SP", "27": "TO",
}


def normalizar(numero: object) -> str | None:
    """Aceita o número com ou sem pontuação e devolve no formato padrão, ou None se inválido."""
    texto = re.sub(r"\s", "", str(numero or ""))
    if PADRAO.match(texto):
        return texto
    digitos = re.sub(r"\D", "", texto)
    if len(digitos) != 20:
        return None
    return f"{digitos[:7]}-{digitos[7:9]}.{digitos[9:13]}.{digitos[13]}.{digitos[14:16]}.{digitos[16:]}"


def validar(numero: object) -> bool:
    return normalizar(numero) is not None


def uf_do_numero(numero: object) -> str | None:
    """UF do tribunal para processos da Justiça Estadual; None para outros segmentos ou inválido."""
    padrao = normalizar(numero)
    if padrao is None:
        return None
    partes = PADRAO.match(padrao)
    assert partes is not None
    _, _, _, justica, tribunal, _ = partes.groups()
    if justica != JUSTICA_ESTADUAL:
        return None
    return TJ_UF.get(tribunal)
