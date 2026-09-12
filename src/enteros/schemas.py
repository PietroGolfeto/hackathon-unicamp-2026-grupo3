"""Contratos pydantic que cruzam fronteiras: entrada do caso e recomendação."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

from enteros import config as cfg

StatusDoc = Literal["presente", "ausente", "inconsistente"]
Decisao = Literal["defesa", "acordo", "instruir"]
Faixa = Literal["verde", "amarela", "vermelha"]


class DocsStatus(BaseModel):
    """Status de cada subsídio. `inconsistente` = existe mas não prova o que deveria (tratado como ausente)."""

    contrato: StatusDoc = cfg.STATUS_AUSENTE
    extrato: StatusDoc = cfg.STATUS_AUSENTE
    comprovante: StatusDoc = cfg.STATUS_AUSENTE
    dossie: StatusDoc = cfg.STATUS_AUSENTE
    demonstrativo: StatusDoc = cfg.STATUS_AUSENTE
    laudo: StatusDoc = cfg.STATUS_AUSENTE

    def flags(self) -> dict[str, int]:
        return {d: int(getattr(self, d) == cfg.STATUS_PRESENTE) for d in cfg.DOCS}

    def ausentes(self) -> list[str]:
        return [d for d in cfg.DOCS if getattr(self, d) != cfg.STATUS_PRESENTE]


class CaseFeatures(BaseModel):
    """O que o engine precisa saber de um processo. Campos opcionais vêm da trilha de IA documental."""

    numero: str | None = None
    uf: str
    sub_assunto: str = cfg.SUB_GOLPE
    valor_causa: float = Field(gt=0)
    docs: DocsStatus = DocsStatus()
    # extraídos dos autos/subsídios pela IA (opcionais)
    conta_deposito_titular_autor: bool | None = None
    liveness_presente: bool | None = None
    parcelas_pagas: int | None = None
    valor_parcela: float | None = None
    saldo_devedor: float | None = None
    dano_moral_pedido: float | None = None
    contradicoes: list[str] = []
    red_flags: list[str] = []

    @field_validator("uf")
    @classmethod
    def _uf(cls, v: str) -> str:
        v = v.strip().upper()
        if v not in cfg.UFS:
            raise ValueError(f"UF desconhecida: {v}")
        return v

    @field_validator("sub_assunto")
    @classmethod
    def _sub(cls, v: str) -> str:
        v = v.strip().capitalize()
        if v not in cfg.SUB_ASSUNTOS:
            raise ValueError(f"sub-assunto desconhecido: {v} (esperado {cfg.SUB_ASSUNTOS})")
        return v


class Escada(BaseModel):
    abertura: float
    alvo: float
    teto: float
    piso: float
    p_aceite_alvo: float


class Decomposicao(BaseModel):
    devolucao_parcelas: float
    saldo_baixado: float
    dano_moral: float


class Recomendacao(BaseModel):
    decisao: Decisao
    faixa: Faixa
    decisao_se_nao_recuperar: Decisao | None = None
    p_perda: float
    p_perda_intervalo: tuple[float, float]
    condenacao_esperada: float
    condenacao_p20: float
    condenacao_p50: float
    condenacao_p80: float
    ev_defesa: float
    ev_acordo: float | None
    economia_esperada: float
    escada: Escada | None
    decomposicao: Decomposicao | None
    voi_por_doc: dict[str, float]
    docs_a_solicitar: list[str]
    motivos: list[str]
    regras_acionadas: list[str]
    contribuicoes: list[dict]
    versao_politica: str
    versao_modelo: str
