"""As 8 tabelas. Colunas jsonb: sempre atribuir um dict/list novo, nunca mutar in place."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

Json = JSONB


class Escritorio(Base):
    __tablename__ = "escritorios"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(120), unique=True)


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    senha_hash: Mapped[str] = mapped_column(String(100))
    papel: Mapped[str] = mapped_column(String(20))  # advogado | gestor
    escritorio_id: Mapped[int | None] = mapped_column(ForeignKey("escritorios.id"))

    escritorio: Mapped[Escritorio | None] = relationship(lazy="joined")

    @property
    def escritorio_nome(self) -> str | None:
        return self.escritorio.nome if self.escritorio else None


class Processo(Base):
    __tablename__ = "processos"

    id: Mapped[int] = mapped_column(primary_key=True)
    numero: Mapped[str] = mapped_column(String(25), unique=True, index=True)
    uf: Mapped[str] = mapped_column(String(2))
    sub_assunto: Mapped[str | None] = mapped_column(String(40))
    valor_causa: Mapped[float] = mapped_column(Float)
    escritorio_id: Mapped[int] = mapped_column(ForeignKey("escritorios.id"), index=True)
    origem: Mapped[str] = mapped_column(String(20))  # exemplo | sintetico
    subsidios: Mapped[dict[str, Any]] = mapped_column(Json, default=dict)
    documentos: Mapped[list[dict[str, Any]]] = mapped_column(Json, default=list)
    dados_extraidos: Mapped[dict[str, Any] | None] = mapped_column(Json)
    analise: Mapped[dict[str, Any] | None] = mapped_column(Json)
    scores: Mapped[dict[str, Any] | None] = mapped_column(Json)
    status: Mapped[str] = mapped_column(String(20), default="pendente")  # pendente|decidido|encerrado
    reservado_ate: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    escritorio: Mapped[Escritorio] = relationship(lazy="joined")


class HistoricoSentenca(Base):
    """60k sentenças da Enter + scores out-of-fold. Cacheada em DataFrame na API."""

    __tablename__ = "historico_sentencas"

    numero: Mapped[str] = mapped_column(String(25), primary_key=True)
    uf: Mapped[str | None] = mapped_column(String(2))
    sub_assunto: Mapped[str | None] = mapped_column(String(40))
    valor_causa: Mapped[float | None] = mapped_column(Float)
    resultado_macro: Mapped[int | None] = mapped_column(Integer)  # 1 êxito, 0 não êxito
    resultado_micro: Mapped[str | None] = mapped_column(String(40))
    valor_condenacao: Mapped[float | None] = mapped_column(Float)
    contrato: Mapped[bool] = mapped_column(Boolean, default=False)
    extrato: Mapped[bool] = mapped_column(Boolean, default=False)
    comprovante_credito: Mapped[bool] = mapped_column(Boolean, default=False)
    dossie: Mapped[bool] = mapped_column(Boolean, default=False)
    demonstrativo_divida: Mapped[bool] = mapped_column(Boolean, default=False)
    laudo_referenciado: Mapped[bool] = mapped_column(Boolean, default=False)
    p_exito_oof: Mapped[float | None] = mapped_column(Float)
    condenacao_p20_oof: Mapped[float | None] = mapped_column(Float)
    condenacao_p50_oof: Mapped[float | None] = mapped_column(Float)
    condenacao_p80_oof: Mapped[float | None] = mapped_column(Float)
    fold: Mapped[int | None] = mapped_column(Integer)
    scores_origem: Mapped[str | None] = mapped_column(String(10))  # modelo | stub


class Politica(Base):
    __tablename__ = "politicas"

    id: Mapped[int] = mapped_column(primary_key=True)
    versao: Mapped[int] = mapped_column(Integer)
    nome: Mapped[str] = mapped_column(String(120))
    params: Mapped[dict[str, Any]] = mapped_column(Json)
    ativa: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    criado_por: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    publicada_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resumo_backtest: Mapped[dict[str, Any] | None] = mapped_column(Json)  # gravado ao ativar


class Recomendacao(Base):
    """O que o advogado viu. UNIQUE (processo, política): a mesma política dá a mesma resposta."""

    __tablename__ = "recomendacoes"
    __table_args__ = (UniqueConstraint("processo_id", "politica_id", name="uq_rec_processo_politica"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    processo_id: Mapped[int] = mapped_column(ForeignKey("processos.id"), index=True)
    politica_id: Mapped[int] = mapped_column(ForeignKey("politicas.id"))
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"))
    tipo: Mapped[str] = mapped_column(String(10))  # acordo | defesa
    valor_sugerido: Mapped[float | None] = mapped_column(Float)
    valor_min: Mapped[float | None] = mapped_column(Float)
    valor_max: Mapped[float | None] = mapped_column(Float)
    custo_esperado_defesa: Mapped[float] = mapped_column(Float)
    custo_esperado_acordo: Mapped[float] = mapped_column(Float)
    economia_esperada: Mapped[float] = mapped_column(Float)
    regra: Mapped[str] = mapped_column(String(20))
    sinais_acionados: Mapped[list[str]] = mapped_column(Json, default=list)
    motivos: Mapped[list[str]] = mapped_column(Json, default=list)
    scores_snapshot: Mapped[dict[str, Any]] = mapped_column(Json)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Decisao(Base):
    """Append-only. A decisão atual de um processo é a mais recente. Negociação são 3 colunas."""

    __tablename__ = "decisoes"

    id: Mapped[int] = mapped_column(primary_key=True)
    processo_id: Mapped[int] = mapped_column(ForeignKey("processos.id"), index=True)
    recomendacao_id: Mapped[int] = mapped_column(ForeignKey("recomendacoes.id"))
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), index=True)
    tipo: Mapped[str] = mapped_column(String(10))  # acordo | defesa
    valor_proposto: Mapped[float | None] = mapped_column(Float)
    justificativa: Mapped[str | None] = mapped_column(Text)
    aderente: Mapped[bool] = mapped_column(Boolean)
    tipo_desvio: Mapped[str] = mapped_column(String(10))  # nenhum | tipo | valor
    status: Mapped[str] = mapped_column(String(20))  # registrada|pendente_aprovacao|aprovada|rejeitada
    tempo_analise_s: Mapped[int | None] = mapped_column(Integer)
    documentos_abertos: Mapped[list[str]] = mapped_column(Json, default=list)
    resultado: Mapped[str | None] = mapped_column(String(25))
    valor_final: Mapped[float | None] = mapped_column(Float)
    resultado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    observacao: Mapped[str | None] = mapped_column(Text)
    aprovado_por: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"))
    comentario_aprovacao: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    recomendacao: Mapped[Recomendacao] = relationship(lazy="joined")
    usuario: Mapped[Usuario] = relationship(foreign_keys=[usuario_id], lazy="joined")

    @property
    def usuario_nome(self) -> str | None:
        return self.usuario.nome if self.usuario else None


class Evento(Base):
    __tablename__ = "eventos"

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), index=True)
    processo_id: Mapped[int | None] = mapped_column(ForeignKey("processos.id"), index=True)
    tipo: Mapped[str] = mapped_column(String(30))  # abriu_caso | viu_recomendacao | abriu_documento
    payload: Mapped[dict[str, Any]] = mapped_column(Json, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


RESULTADOS_NEGOCIACAO = ("aceito", "recusado", "contraproposta_aceita", "sem_resposta", "seguiu_defesa")
