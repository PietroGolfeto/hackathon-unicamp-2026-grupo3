"""Acordos fora da banda ou acima do teto de valor da causa esperam o gestor."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import Gestor
from app.db import get_db
from app.models import Decisao, Processo
from app.schemas import AprovacaoIn, AprovacaoOut, DecisaoOut, RecomendacaoResumo

router = APIRouter(tags=["aprovacoes"])
Db = Annotated[Session, Depends(get_db)]


@router.get("/aprovacoes", response_model=list[AprovacaoOut])
def listar(_: Gestor, db: Db, situacao: Annotated[str, ...] = "pendente_aprovacao") -> list[AprovacaoOut]:
    q = (select(Decisao, Processo).join(Processo, Processo.id == Decisao.processo_id)
         .where(Decisao.status == situacao).order_by(Decisao.created_at.desc()))
    saida = []
    for decisao, processo in db.execute(q):
        autor = ((processo.dados_extraidos or {}).get("autor") or {}).get("nome")
        saida.append(AprovacaoOut(
            decisao=DecisaoOut.model_validate(decisao), processo_id=processo.id,
            numero=processo.numero, valor_causa=processo.valor_causa,
            escritorio=processo.escritorio.nome, autor=autor,
            recomendacao=RecomendacaoResumo.model_validate(decisao.recomendacao),
        ))
    return saida


@router.post("/aprovacoes/{decisao_id}", response_model=DecisaoOut)
def decidir(decisao_id: int, dados: AprovacaoIn, gestor: Gestor, db: Db) -> Decisao:
    decisao = db.get(Decisao, decisao_id)
    if decisao is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Decisão não encontrada.")
    if decisao.status != "pendente_aprovacao":
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Esta decisão não está pendente.")
    decisao.status = "aprovada" if dados.acao == "aprovar" else "rejeitada"
    decisao.aprovado_por = gestor.id
    decisao.comentario_aprovacao = (dados.comentario or "").strip() or None
    db.commit()
    db.refresh(decisao)
    return decisao
