"""Números para o painel do gestor. P5 plota; aqui só agregados."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import Gestor
from app.db import get_db
from app.models import Politica
from app.services import metricas, parecer_ia

router = APIRouter(prefix="/dashboard", tags=["dashboard"])
Db = Annotated[Session, Depends(get_db)]


@router.get("/aderencia")
def aderencia(_: Gestor, db: Db, escritorio_id: int | None = None,
              desde: datetime | None = None) -> dict[str, Any]:
    return metricas.aderencia(db, escritorio_id, desde)


@router.get("/efetividade")
def efetividade(request: Request, _: Gestor, db: Db, desde: datetime | None = None) -> dict[str, Any]:
    politica = db.scalar(select(Politica).where(Politica.ativa).order_by(Politica.id.desc()))
    return metricas.efetividade(db, desde, politica, request.app.state.modelo.info())


@router.post("/desvios/{decisao_id}/parecer")
def gerar_parecer(decisao_id: int, _: Gestor, db: Db) -> dict[str, Any]:
    """Gere ou retorne o parecer consultivo de uma decisão divergente.

    Args:
        decisao_id: Identificador da decisão a analisar.
        db: Sessão transacional do banco.

    Returns:
        Parecer estruturado e persistido.

    Raises:
        HTTPException: Se a decisão for inválida ou o provedor estiver indisponível.
    """
    try:
        return parecer_ia.obter_ou_gerar(db, decisao_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except parecer_ia.ParecerIndisponivel as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
