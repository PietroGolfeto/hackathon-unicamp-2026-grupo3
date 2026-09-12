"""Normalização de colunas e valores dos CSVs da Enter.

Os dois arquivos entregues pela organização têm cabeçalhos com acento, caixa mista e uma
inconsistência ("Número do processo" num arquivo, "Número do processos" no outro). Tudo que
lê CSV no projeto passa por aqui para que api, model e extractor usem os mesmos nomes.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable

# nome canônico -> variantes aceitas, já normalizadas (sem acento, minúsculas, espaços únicos)
ALIASES: dict[str, tuple[str, ...]] = {
    "numero": ("numero do processo", "numero do processos", "numero processo", "processo"),
    "uf": ("uf",),
    "assunto": ("assunto",),
    "sub_assunto": ("sub-assunto", "sub assunto", "subassunto"),
    "resultado_macro": ("resultado macro",),
    "resultado_micro": ("resultado micro",),
    "valor_causa": ("valor da causa",),
    "valor_condenacao": (
        "valor da condenacao/indenizacao",
        "valor da condenacao",
        "valor condenacao",
    ),
    "contrato": ("contrato",),
    "extrato": ("extrato",),
    "comprovante_credito": ("comprovante de credito",),
    "dossie": ("dossie",),
    "demonstrativo_divida": ("demonstrativo de evolucao da divida", "demonstrativo divida"),
    "laudo_referenciado": ("laudo referenciado",),
}

FLAGS_SUBSIDIOS: tuple[str, ...] = (
    "contrato",
    "extrato",
    "comprovante_credito",
    "dossie",
    "demonstrativo_divida",
    "laudo_referenciado",
)

_INVERSO: dict[str, str] = {
    alias: canonico for canonico, aliases in ALIASES.items() for alias in aliases
}


def normalizar_nome(nome: object) -> str:
    """Remove acentos, baixa a caixa e colapsa espaços. "Sub-assunto " -> "sub-assunto"."""
    decomposto = unicodedata.normalize("NFKD", str(nome))
    sem_acento = "".join(c for c in decomposto if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", sem_acento.strip().lower())


def mapear_colunas(colunas: Iterable[object]) -> dict[str, str]:
    """Devolve {nome original: nome canônico} só para as colunas reconhecidas.

    Uso típico: df.rename(columns=mapear_colunas(df.columns)).
    """
    mapa: dict[str, str] = {}
    for original in colunas:
        canonico = _INVERSO.get(normalizar_nome(original))
        if canonico:
            mapa[str(original)] = canonico
    return mapa


def parse_brl(valor: object) -> float | None:
    """Converte dinheiro em formato brasileiro para float.

    "13.534,00" -> 13534.0 · "R$ 1.000,50" -> 1000.5 · "7.714,38" -> 7714.38 ·
    "" / None / "NaN" -> None · números passam direto (NaN vira None).
    Também aceita formato americano ("1,234.50") e número puro ("1000.5").
    """
    if valor is None:
        return None
    if isinstance(valor, bool):
        return float(valor)
    if isinstance(valor, (int, float)):
        return None if valor != valor else float(valor)  # NaN != NaN

    texto = str(valor).strip()
    if not texto or texto.lower() in {"nan", "none", "null", "-"}:
        return None

    texto = re.sub(r"[R$\s]", "", texto)
    if re.fullmatch(r"-?\d{1,3}(\.\d{3})+(,\d+)?", texto) or re.fullmatch(r"-?\d+,\d+", texto):
        texto = texto.replace(".", "").replace(",", ".")  # brasileiro
    elif re.fullmatch(r"-?\d{1,3}(,\d{3})+(\.\d+)?", texto):
        texto = texto.replace(",", "")  # americano
    try:
        return float(texto)
    except ValueError:
        return None


def resultado_macro_para_int(valor: object) -> int | None:
    """"Êxito" -> 1 · "Não Êxito" -> 0 · 1/0/True/False passam · resto -> None."""
    if isinstance(valor, bool):
        return int(valor)
    if isinstance(valor, (int, float)):
        return None if valor != valor else int(valor)
    texto = normalizar_nome(valor or "")
    if texto in {"exito", "1", "true", "sim"}:
        return 1
    if texto in {"nao exito", "0", "false", "nao"}:
        return 0
    return None
