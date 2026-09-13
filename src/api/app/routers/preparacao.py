"""Dispara e acompanha a preparação dos casos que a tela do advogado lista."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import UsuarioLogado
from app.db import get_db
from app.models import Escritorio
from app.schemas import PreparacaoOut
from app.services import preparacao as svc

router = APIRouter(tags=["preparacao"])
Db = Annotated[Session, Depends(get_db)]


@router.post("/preparacao", response_model=PreparacaoOut, status_code=status.HTTP_202_ACCEPTED)
def preparar(request: Request, usuario: UsuarioLogado, db: Db) -> PreparacaoOut:
    """Idempotente: se já está rodando ou já terminou, só devolve o estado."""
    escritorio_id = usuario.escritorio_id or db.scalar(select(Escritorio.id).order_by(Escritorio.id))
    return PreparacaoOut.model_validate(svc.iniciar(request.app, escritorio_id))


@router.get("/preparacao", response_model=PreparacaoOut)
def progresso(request: Request, usuario: UsuarioLogado, db: Db) -> PreparacaoOut:
    return PreparacaoOut.model_validate(svc.status(db, request.app.state.extrator is not None))
