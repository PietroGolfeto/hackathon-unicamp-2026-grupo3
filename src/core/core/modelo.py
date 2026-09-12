"""Contrato de P1: o modelo entrega scores por caso; a política decide em cima deles."""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Protocol

from pydantic import BaseModel, Field

from core.caso import CasoFeatures


class Contribuicao(BaseModel):
    feature: str
    valor: str | float | bool | None = None
    contribuicao: float  # sinal positivo empurra para êxito do banco
    descricao: str | None = None


class Scores(BaseModel):
    numero: str
    modelo_versao: str
    origem: Literal["modelo", "stub"]
    p_exito_defesa: float = Field(ge=0, le=1)  # P(banco vence)
    condenacao_p20: float = Field(ge=0)  # condicionais a perder
    condenacao_p50: float = Field(ge=0)
    condenacao_p80: float = Field(ge=0)
    contribuicoes: list[Contribuicao] = Field(default_factory=list)  # top 5, com sinal
    gerado_em: datetime


class CalibracaoBin(BaseModel):
    p_min: float
    p_max: float
    n: int
    p_prevista_media: float
    taxa_exito_real: float


class ModeloInfo(BaseModel):
    versao: str
    treinado_em: datetime
    n_treino: int
    metricas: dict[str, float] = Field(default_factory=dict)
    calibracao: list[CalibracaoBin] = Field(default_factory=list)
    importancias: dict[str, float] = Field(default_factory=dict)


class ModeloScores(Protocol):
    def score(self, caso: CasoFeatures) -> Scores: ...

    def score_batch(self, casos: list[CasoFeatures]) -> list[Scores]: ...

    def info(self) -> ModeloInfo: ...


# Colunas fixas de data/derived/historico_scored.csv (entregue por P1)
COLUNAS_HISTORICO_SCORED: tuple[str, ...] = (
    "numero", "uf", "sub_assunto", "resultado_macro", "resultado_micro", "valor_causa",
    "valor_condenacao", "contrato", "extrato", "comprovante_credito", "dossie",
    "demonstrativo_divida", "laudo_referenciado", "p_exito_oof", "condenacao_p20_oof",
    "condenacao_p50_oof", "condenacao_p80_oof", "fold",
)
