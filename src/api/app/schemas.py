"""Modelos de entrada e saída da API (pydantic v2). Dinheiro em número; formatação só no front."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from core.politica import PoliticaParams
from pydantic import BaseModel, ConfigDict, Field

TipoDecisao = Literal["acordo", "defesa"]
ResultadoNegociacao = Literal[
    "aceito", "recusado", "contraproposta_aceita", "sem_resposta", "seguiu_defesa"
]


class Saida(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class LoginIn(BaseModel):
    email: str = Field(min_length=3, max_length=120)
    senha: str = Field(min_length=1, max_length=200)


class UsuarioOut(Saida):
    id: int
    nome: str
    email: str
    papel: str
    escritorio_id: int | None
    escritorio_nome: str | None


class RecomendacaoResumo(Saida):
    id: int
    politica_id: int
    tipo: str
    valor_sugerido: float | None
    valor_min: float | None
    valor_max: float | None
    created_at: datetime


class ProcessoResumo(BaseModel):
    id: int
    numero: str
    uf: str
    sub_assunto: str | None
    valor_causa: float
    autor: str | None
    status: str
    origem: str
    escritorio_id: int
    escritorio: str
    n_subsidios: int
    sinais: list[str]
    scores_origem: str | None
    extracao_origem: str | None
    recomendacao: RecomendacaoResumo | None
    decisao_tipo: str | None
    decisao_status: str | None
    reservado_ate: datetime | None


class PreparacaoOut(BaseModel):
    """Progresso da inferência dos casos; o front faz poll enquanto está `rodando`."""

    status: Literal["ocioso", "rodando", "pronto", "erro"]
    total: int
    prontos: int
    atual: str | None = None
    erro: str | None = None
    atualizado_em: datetime | None = None


class DocumentoOut(BaseModel):
    tipo: str  # autos | subsidios
    arquivo: str
    url: str
    # da extração de P3; None quando não houve extração (decisão 27)
    comentario: str | None = None
    relevancia: str | None = None


class DecisaoOut(Saida):
    id: int
    processo_id: int
    recomendacao_id: int
    usuario_id: int
    usuario_nome: str | None
    tipo: str
    valor_proposto: float | None
    justificativa: str | None
    aderente: bool
    tipo_desvio: str
    status: str
    tempo_analise_s: int | None
    documentos_abertos: list[str]
    resultado: str | None
    valor_final: float | None
    resultado_em: datetime | None
    observacao: str | None
    comentario_aprovacao: str | None
    created_at: datetime


class ProcessoDetalhe(BaseModel):
    id: int
    numero: str
    uf: str
    sub_assunto: str | None
    valor_causa: float
    status: str
    origem: str
    escritorio_id: int
    escritorio: str
    subsidios: dict[str, bool]
    documentos: list[DocumentoOut]
    dados_extraidos: dict[str, Any] | None
    analise: dict[str, Any] | None
    sinais: list[dict[str, Any]]
    scores: dict[str, Any] | None
    decisao_atual: DecisaoOut | None
    reservado_ate: datetime | None
    created_at: datetime


class RecomendacaoOut(Saida):
    id: int
    processo_id: int
    politica_id: int
    politica_versao: int
    politica_nome: str
    tipo: str  # acordo | defesa | instruir
    valor_sugerido: float | None
    valor_min: float | None
    valor_max: float | None
    custo_esperado_defesa: float
    custo_esperado_acordo: float
    economia_esperada: float
    regra: str
    sinais_acionados: list[str]
    docs_a_solicitar: list[str] = []
    motivos: list[str]
    scores_snapshot: dict[str, Any]
    exige_aprovacao_valor_causa: bool
    created_at: datetime


class DecisaoIn(BaseModel):
    tipo: TipoDecisao
    valor_proposto: float | None = Field(default=None, ge=0)
    justificativa: str | None = Field(default=None, max_length=2000)
    tempo_analise_s: int | None = Field(default=None, ge=0)
    documentos_abertos: list[str] = Field(default_factory=list)


class DecisaoRegistrada(BaseModel):
    decisao: DecisaoOut
    recomendacao: RecomendacaoOut
    minutas: dict[str, Any] | None
    contato_adverso: dict[str, Any] | None
    mensagem: str


class ResultadoIn(BaseModel):
    resultado: ResultadoNegociacao
    valor_final: float | None = Field(default=None, ge=0)
    observacao: str | None = Field(default=None, max_length=2000)


class EventoIn(BaseModel):
    processo_id: int | None = None
    tipo: str = Field(min_length=1, max_length=30)
    payload: dict[str, Any] = Field(default_factory=dict)


class PoliticaIn(BaseModel):
    nome: str = Field(min_length=1, max_length=120)
    params: PoliticaParams


class SimularIn(BaseModel):
    params: PoliticaParams


class PoliticaOut(Saida):
    id: int
    versao: int
    nome: str
    params: dict[str, Any]
    ativa: bool
    criado_por: int | None
    created_at: datetime
    publicada_em: datetime | None
    resumo_backtest: dict[str, Any] | None


class AprovacaoIn(BaseModel):
    acao: Literal["aprovar", "rejeitar"]
    comentario: str | None = Field(default=None, max_length=2000)


class AprovacaoOut(BaseModel):
    decisao: DecisaoOut
    processo_id: int
    numero: str
    valor_causa: float
    escritorio: str
    autor: str | None
    recomendacao: RecomendacaoResumo
