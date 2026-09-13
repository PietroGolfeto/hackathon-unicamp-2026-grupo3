"""Recomendação gravada sob a política ativa (get_or_create) e regras de aderência/aprovação."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from core.caso import CasoFeatures, Subsidios
from core.modelo import ModeloScores, Scores
from core.politica import PoliticaParams, aplicar
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.models import Evento, Politica, Processo, Recomendacao, Usuario
from app.schemas import DecisaoIn, RecomendacaoOut


def politica_ativa(db: Session) -> Politica:
    politica = db.scalar(select(Politica).where(Politica.ativa).order_by(Politica.id.desc()))
    if politica is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE,
                            detail="Nenhuma política ativa. O gestor precisa publicar uma.")
    return politica


def params_de(politica: Politica) -> PoliticaParams:
    return PoliticaParams.model_validate(politica.params)


def caso_de(processo: Processo) -> CasoFeatures:
    dados = processo.dados_extraidos or {}
    sinais = {s["codigo"]: True for s in dados.get("sinais_alerta", []) if s.get("codigo")}
    return CasoFeatures(
        numero=processo.numero, uf=processo.uf, sub_assunto=processo.sub_assunto,
        valor_causa=processo.valor_causa, subsidios=Subsidios(**(processo.subsidios or {})),
        sinais=sinais,
    )


def scores_de(db: Session, processo: Processo, modelo: ModeloScores) -> Scores:
    if processo.scores:
        return Scores.model_validate(processo.scores)
    scores = modelo.score(caso_de(processo))
    processo.scores = scores.model_dump(mode="json")
    db.commit()
    return scores


def obter_ou_criar(
    db: Session, processo: Processo, usuario: Usuario | None, politica: Politica, modelo: ModeloScores
) -> Recomendacao:
    """UNIQUE (processo, política) + INSERT … ON CONFLICT DO NOTHING: dois jurados, uma linha."""
    existente = db.scalar(select(Recomendacao).where(
        Recomendacao.processo_id == processo.id, Recomendacao.politica_id == politica.id))
    if existente:
        return existente
    rec = aplicar(scores_de(db, processo, modelo), caso_de(processo), params_de(politica), politica.id)
    db.execute(
        pg_insert(Recomendacao).values(
            processo_id=processo.id, politica_id=politica.id,
            usuario_id=usuario.id if usuario else None, tipo=rec.tipo,
            valor_sugerido=rec.valor_sugerido, valor_min=rec.valor_min, valor_max=rec.valor_max,
            custo_esperado_defesa=rec.custo_esperado_defesa,
            custo_esperado_acordo=rec.custo_esperado_acordo, economia_esperada=rec.economia_esperada,
            regra=rec.regra, sinais_acionados=rec.sinais_acionados,
            docs_a_solicitar=rec.docs_a_solicitar, motivos=rec.motivos,
            scores_snapshot=rec.scores_snapshot.model_dump(mode="json"),
        ).on_conflict_do_nothing(constraint="uq_rec_processo_politica")
    )
    db.commit()
    criada = db.scalar(select(Recomendacao).where(
        Recomendacao.processo_id == processo.id, Recomendacao.politica_id == politica.id))
    assert criada is not None
    return criada


def para_saida(rec: Recomendacao, politica: Politica, processo: Processo) -> RecomendacaoOut:
    prm = params_de(politica)
    teto = prm.valor_causa_max_sem_aprovacao
    return RecomendacaoOut(
        id=rec.id, processo_id=rec.processo_id, politica_id=rec.politica_id,
        politica_versao=politica.versao, politica_nome=politica.nome, tipo=rec.tipo,
        valor_sugerido=rec.valor_sugerido, valor_min=rec.valor_min, valor_max=rec.valor_max,
        custo_esperado_defesa=rec.custo_esperado_defesa,
        custo_esperado_acordo=rec.custo_esperado_acordo, economia_esperada=rec.economia_esperada,
        regra=rec.regra, sinais_acionados=list(rec.sinais_acionados or []),
        docs_a_solicitar=list(rec.docs_a_solicitar or []),
        motivos=list(rec.motivos or []), scores_snapshot=dict(rec.scores_snapshot or {}),
        exige_aprovacao_valor_causa=teto is not None and processo.valor_causa > teto,
        created_at=rec.created_at,
    )


def avaliar_decisao(
    rec: Recomendacao, dados: DecisaoIn, prm: PoliticaParams, valor_causa: float
) -> tuple[bool, str, str]:
    """(aderente, tipo_desvio, status). Divergência sem justificativa é erro 422."""
    if dados.tipo == "acordo" and dados.valor_proposto is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT,
                            detail="Informe o valor proposto para o acordo.")
    na_banda = (
        dados.tipo == "acordo" and rec.valor_min is not None and rec.valor_max is not None
        and dados.valor_proposto is not None
        and rec.valor_min - 0.01 <= dados.valor_proposto <= rec.valor_max + 0.01
    )
    # O advogado só decide acordo ou defesa. "instruir" é um acordo adiado até os subsídios chegarem:
    # acordar na banda continua aderente; defender é que é desvio.
    esperado = "acordo" if rec.tipo == "instruir" else rec.tipo
    aderente = dados.tipo == esperado and (dados.tipo != "acordo" or na_banda)
    tipo_desvio = "nenhum" if aderente else ("tipo" if dados.tipo != esperado else "valor")
    if not aderente and not (dados.justificativa or "").strip():
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="A decisão diverge da recomendação: informe a justificativa.",
        )
    teto = prm.valor_causa_max_sem_aprovacao
    precisa_aprovacao = dados.tipo == "acordo" and (
        not na_banda or (teto is not None and valor_causa > teto)
    )
    return aderente, tipo_desvio, "pendente_aprovacao" if precisa_aprovacao else "registrada"


def registrar_evento(
    db: Session, usuario_id: int | None, processo_id: int | None, tipo: str,
    payload: dict[str, Any] | None = None, commit: bool = True,
) -> None:
    db.add(Evento(usuario_id=usuario_id, processo_id=processo_id, tipo=tipo, payload=payload or {}))
    if commit:
        db.commit()


def agora() -> datetime:
    return datetime.now(UTC)


def rec_core_de(rec: Recomendacao):
    """Reconstrói o contrato de core a partir da linha gravada (para redigir minutas)."""
    from core.politica import Recomendacao as RecCore

    return RecCore(
        tipo=rec.tipo, valor_sugerido=rec.valor_sugerido, valor_min=rec.valor_min,
        valor_max=rec.valor_max, custo_esperado_defesa=rec.custo_esperado_defesa,
        custo_esperado_acordo=rec.custo_esperado_acordo, economia_esperada=rec.economia_esperada,
        regra=rec.regra, sinais_acionados=list(rec.sinais_acionados or []),
        docs_a_solicitar=list(rec.docs_a_solicitar or []),
        motivos=list(rec.motivos or []), scores_snapshot=Scores.model_validate(rec.scores_snapshot),
        politica_id=rec.politica_id,
    )
