"""Números para o painel do gestor. P5 plota; aqui só agregados."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import Gestor
from app.db import get_db
from app.models import Politica
from app.services import metricas

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
