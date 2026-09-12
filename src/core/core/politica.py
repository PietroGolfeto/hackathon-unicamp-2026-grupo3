"""Política de acordos: função pura sobre scores + parâmetros versionados.

Uma única implementação em numpy serve tanto para um caso (escalares) quanto para os 60 mil
do histórico (colunas). Scores são a saída cara do modelo; aqui só há aritmética barata, o que
permite ao gestor simular parâmetros em tempo real e à API gravar a recomendação exata que o
advogado viu.
"""

from __future__ import annotations

from typing import Any, Literal

import numpy as np
from pydantic import BaseModel, Field, model_validator

from core.caso import CODIGOS_SINAIS, CasoFeatures
from core.modelo import Scores

Regra = Literal["defesa_forte", "acordo_forte", "custo", "sinal"]


class PoliticaParams(BaseModel):
    custas_fixas_defesa: float = Field(default=1500, ge=0)
    honorarios_defesa_pct: float = Field(default=0.10, ge=0, le=1)
    sucumbencia_pct: float = Field(default=0.10, ge=0, le=1)
    custo_operacional_acordo: float = Field(default=300, ge=0)
    taxa_aceite_esperada: float = Field(default=0.65, ge=0, le=1)
    fator_oferta: float = Field(default=0.80, ge=0, le=2)  # fração do prejuízo esperado
    piso_oferta_pct_causa: float = Field(default=0.10, ge=0, le=1)
    teto_oferta_pct_causa: float = Field(default=0.60, ge=0, le=1)
    margem_banda_pct: float = Field(default=0.15, ge=0, le=1)
    arredondamento: float = Field(default=50, gt=0)
    limiar_defesa_forte: float = Field(default=0.85, ge=0, le=1)
    limiar_acordo_forte: float = Field(default=0.30, ge=0, le=1)
    sinais_forcam_acordo: list[str] = Field(default_factory=lambda: ["CREDITO_CONTA_TERCEIRO"])
    valor_causa_max_sem_aprovacao: float | None = Field(default=50000, ge=0)
    incluir_extincao_no_backtest: bool = True

    @model_validator(mode="after")
    def _coerente(self) -> PoliticaParams:
        if self.limiar_acordo_forte > self.limiar_defesa_forte:
            raise ValueError("limiar_acordo_forte deve ser menor ou igual a limiar_defesa_forte")
        if self.piso_oferta_pct_causa > self.teto_oferta_pct_causa:
            raise ValueError("piso_oferta_pct_causa deve ser menor ou igual a teto_oferta_pct_causa")
        return self


class Recomendacao(BaseModel):
    tipo: Literal["acordo", "defesa"]
    valor_sugerido: float | None = None
    valor_min: float | None = None
    valor_max: float | None = None
    custo_esperado_defesa: float
    custo_esperado_acordo: float
    economia_esperada: float  # custo_defesa - custo_acordo; positivo favorece acordo
    regra: Regra
    sinais_acionados: list[str] = Field(default_factory=list)
    motivos: list[str]
    scores_snapshot: Scores
    politica_id: int


def calcular(
    p_exito: Any,
    cond_p20: Any,
    cond_p50: Any,
    cond_p80: Any,
    valor_causa: Any,
    prm: PoliticaParams,
    sinais_forcam: Any | None = None,
) -> dict[str, np.ndarray]:
    """Núcleo da política. Aceita escalares ou arrays (numpy, pandas) do mesmo tamanho.

    Devolve arrays: acordo (bool), oferta, valor_min, valor_max, custo_defesa, custo_acordo,
    economia (custo_defesa - custo_acordo), regra (str), oferta_limitada ("piso"/"teto"/"").
    """
    p = np.clip(np.asarray(p_exito, dtype=float), 0.0, 1.0)
    c50 = np.asarray(cond_p50, dtype=float)
    c80 = np.asarray(cond_p80, dtype=float)
    causa = np.asarray(valor_causa, dtype=float)
    q = 1.0 - p

    custo_defesa = (
        prm.custas_fixas_defesa
        + prm.honorarios_defesa_pct * causa
        + q * c50 * (1.0 + prm.sucumbencia_pct)
    )

    bruta = np.round(prm.fator_oferta * q * c50 / prm.arredondamento) * prm.arredondamento
    piso = prm.piso_oferta_pct_causa * causa
    teto = np.maximum(np.minimum(prm.teto_oferta_pct_causa * causa, c80), piso)
    oferta = np.clip(bruta, piso, teto)
    oferta_limitada = np.where(bruta < piso, "piso", np.where(bruta > teto, "teto", ""))

    a = prm.taxa_aceite_esperada
    op = prm.custo_operacional_acordo
    custo_acordo = a * (oferta + op) + (1.0 - a) * (custo_defesa + op)

    forte_defesa = p >= prm.limiar_defesa_forte
    forte_acordo = p <= prm.limiar_acordo_forte
    acordo = np.where(forte_defesa, False, np.where(forte_acordo, True, custo_acordo < custo_defesa))
    regra = np.where(forte_defesa, "defesa_forte", np.where(forte_acordo, "acordo_forte", "custo"))
    if sinais_forcam is not None:
        forca = np.asarray(sinais_forcam, dtype=bool)
        acordo = acordo | forca
        regra = np.where(forca, "sinal", regra)

    return {
        "acordo": np.asarray(acordo, dtype=bool),
        "oferta": oferta,
        "valor_min": oferta * (1.0 - prm.margem_banda_pct),
        "valor_max": oferta * (1.0 + prm.margem_banda_pct),
        "custo_defesa": custo_defesa,
        "custo_acordo": custo_acordo,
        "economia": custo_defesa - custo_acordo,
        "regra": regra,
        "oferta_limitada": oferta_limitada,
    }


def custos_reais(
    p_exito: Any,
    cond_p20: Any,
    cond_p50: Any,
    cond_p80: Any,
    valor_causa: Any,
    perdeu: Any,
    valor_condenacao: Any,
    prm: PoliticaParams,
    sinais_forcam: Any | None = None,
) -> dict[str, np.ndarray]:
    """Backtest: o que a política teria custado usando o resultado real de cada processo.

    custo_defesa_real = custas + honorários·causa + condenação·(1 + sucumbência) se perdeu.
    Onde a política manda acordo, assume a taxa de aceite esperada (hipótese, não dado).
    Também devolve os dois baselines: defender tudo e acordar tudo.
    """
    r = calcular(p_exito, cond_p20, cond_p50, cond_p80, valor_causa, prm, sinais_forcam)
    causa = np.asarray(valor_causa, dtype=float)
    perdeu_b = np.asarray(perdeu, dtype=bool)
    condenacao = np.nan_to_num(np.asarray(valor_condenacao, dtype=float), nan=0.0)

    defesa_real = (
        prm.custas_fixas_defesa
        + prm.honorarios_defesa_pct * causa
        + np.where(perdeu_b, condenacao * (1.0 + prm.sucumbencia_pct), 0.0)
    )
    a = prm.taxa_aceite_esperada
    op = prm.custo_operacional_acordo
    acordo_real = a * (r["oferta"] + op) + (1.0 - a) * (defesa_real + op)
    r["custo_defesa_real"] = defesa_real
    r["custo_acordo_real"] = acordo_real
    r["custo_politica"] = np.where(r["acordo"], acordo_real, defesa_real)
    return r


def sinais_que_forcam(caso: CasoFeatures, prm: PoliticaParams) -> list[str]:
    """Códigos presentes em caso.sinais (com valor verdadeiro) que a política manda acordar."""
    return [c for c in prm.sinais_forcam_acordo if caso.sinais.get(c)]


def aplicar(scores: Scores, caso: CasoFeatures, prm: PoliticaParams, politica_id: int) -> Recomendacao:
    """Aplica a política a um caso e monta os motivos em português."""
    acionados = sinais_que_forcam(caso, prm)
    r = calcular(
        scores.p_exito_defesa,
        scores.condenacao_p20,
        scores.condenacao_p50,
        scores.condenacao_p80,
        caso.valor_causa,
        prm,
        sinais_forcam=bool(acionados),
    )
    acordo = bool(r["acordo"])
    oferta = float(r["oferta"])
    rec = Recomendacao(
        tipo="acordo" if acordo else "defesa",
        valor_sugerido=oferta if acordo else None,
        valor_min=float(r["valor_min"]) if acordo else None,
        valor_max=float(r["valor_max"]) if acordo else None,
        custo_esperado_defesa=float(r["custo_defesa"]),
        custo_esperado_acordo=float(r["custo_acordo"]),
        economia_esperada=float(r["economia"]),
        regra=str(r["regra"]),  # type: ignore[arg-type]
        sinais_acionados=acionados,
        motivos=[],
        scores_snapshot=scores,
        politica_id=politica_id,
    )
    rec.motivos = motivos(rec, scores, caso, prm, str(r["oferta_limitada"]))
    return rec


def brl(valor: float) -> str:
    """R$ 12.345 no padrão brasileiro, sem centavos (motivos são frases, não extrato)."""
    return "R$ " + f"{valor:,.0f}".replace(",", ".")


def pct(valor: float) -> str:
    return f"{valor * 100:.0f}%"


def motivos(
    rec: Recomendacao, scores: Scores, caso: CasoFeatures, prm: PoliticaParams, limitada: str
) -> list[str]:
    """Três frases determinísticas: regra acionada, subsídios, oferta ou custos."""
    p = scores.p_exito_defesa
    frases: list[str] = []

    if rec.regra == "sinal":
        descricoes = [CODIGOS_SINAIS.get(c, c).lower() for c in rec.sinais_acionados]
        frases.append(
            f"Sinal nos autos ({', '.join(descricoes)}) força acordo pela política, "
            f"independentemente da probabilidade de êxito ({pct(p)})."
        )
    elif rec.regra == "defesa_forte":
        frases.append(
            f"Probabilidade de êxito na defesa de {pct(p)}, acima do limiar de defesa forte "
            f"({pct(prm.limiar_defesa_forte)}): a política recomenda defender."
        )
    elif rec.regra == "acordo_forte":
        frases.append(
            f"Probabilidade de êxito na defesa de {pct(p)}, abaixo do limiar de acordo forte "
            f"({pct(prm.limiar_acordo_forte)}): a política recomenda acordo."
        )
    elif rec.tipo == "acordo":
        frases.append(
            f"Probabilidade de êxito na defesa de {pct(p)}: o custo esperado do acordo "
            f"({brl(rec.custo_esperado_acordo)}) é menor que o da defesa "
            f"({brl(rec.custo_esperado_defesa)})."
        )
    else:
        frases.append(
            f"Probabilidade de êxito na defesa de {pct(p)}: o custo esperado da defesa "
            f"({brl(rec.custo_esperado_defesa)}) é menor que o do acordo "
            f"({brl(rec.custo_esperado_acordo)})."
        )

    from core.caso import NOMES_SUBSIDIOS

    presentes = [NOMES_SUBSIDIOS[k].lower() for k in caso.subsidios.presentes()]
    ausentes = [NOMES_SUBSIDIOS[k].lower() for k in caso.subsidios.ausentes()]
    if not presentes:
        frases.append("O banco não forneceu nenhum dos seis subsídios; sem contrato nem extrato, "
                      "o histórico mostra êxito raro.")
    elif not ausentes:
        frases.append("Os seis subsídios estão presentes, inclusive contrato e extrato, "
                      "os dois maiores preditores de êxito.")
    else:
        frases.append(
            f"Subsídios presentes ({len(presentes)} de 6): {', '.join(presentes)}. "
            f"Ausentes: {', '.join(ausentes)}."
        )

    if rec.tipo == "acordo" and rec.valor_sugerido is not None:
        prejuizo = (1 - p) * scores.condenacao_p50
        limite = {
            "piso": f", elevada ao piso de {pct(prm.piso_oferta_pct_causa)} do valor da causa",
            "teto": f", limitada ao teto ({pct(prm.teto_oferta_pct_causa)} da causa ou "
                    f"condenação p80)",
        }.get(limitada, "")
        frases.append(
            f"Oferta sugerida de {brl(rec.valor_sugerido)} (banda {brl(rec.valor_min or 0)} a "
            f"{brl(rec.valor_max or 0)}): {pct(prm.fator_oferta)} do prejuízo esperado de "
            f"{brl(prejuizo)}{limite}."
        )
    else:
        frases.append(
            f"Se perder, a condenação mediana estimada é {brl(scores.condenacao_p50)}; "
            f"defender custa em média {brl(rec.custo_esperado_defesa)} contra "
            f"{brl(rec.custo_esperado_acordo)} de um acordo."
        )
    return frases
