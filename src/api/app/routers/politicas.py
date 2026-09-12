"""Políticas versionadas: listar, criar, simular sobre o histórico, ativar (grava o backtest)."""

from __future__ import annotations

import hmac
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app import plugins
from app.auth import Gestor, UsuarioLogado, usuario_atual
from app.config import settings
from app.db import get_db
from app.models import Politica
from app.schemas import PoliticaIn, PoliticaOut, SimularIn
from app.services import backtest
from app.services.recomendacao import agora, politica_ativa

router = APIRouter(tags=["politicas"])
Db = Annotated[Session, Depends(get_db)]
SEM_HISTORICO = "Histórico não carregado. Coloque os CSVs em data/ e rode `make historico`."


def _historico(request: Request):
    hist = request.app.state.historico
    if hist is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=SEM_HISTORICO)
    return hist


@router.get("/politicas/ativa", response_model=PoliticaOut)
def ativa(_: UsuarioLogado, db: Db) -> Politica:
    return politica_ativa(db)


@router.get("/politicas", response_model=list[PoliticaOut])
def listar(_: Gestor, db: Db) -> list[Politica]:
    return list(db.scalars(select(Politica).order_by(Politica.versao.desc())))


@router.post("/politicas", response_model=PoliticaOut, status_code=status.HTTP_201_CREATED)
def criar(dados: PoliticaIn, gestor: Gestor, db: Db) -> Politica:
    proxima = (db.scalar(select(func.max(Politica.versao))) or 0) + 1
    politica = Politica(versao=proxima, nome=dados.nome.strip(), params=dados.params.model_dump(),
                        ativa=False, criado_por=gestor.id)
    db.add(politica)
    db.commit()
    db.refresh(politica)
    return politica


@router.post("/politicas/simular")
def simular(dados: SimularIn, request: Request, _: Gestor) -> dict[str, Any]:
    """Síncrono de propósito (threadpool): ~60k linhas em dezenas de ms."""
    return backtest.simular(_historico(request), dados.params)


@router.post("/politicas/{politica_id}/ativar", response_model=PoliticaOut)
def ativar(politica_id: int, request: Request, _: Gestor, db: Db) -> Politica:
    politica = db.get(Politica, politica_id)
    if politica is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Política não encontrada.")
    hist = request.app.state.historico
    from core.politica import PoliticaParams

    if hist is not None:
        politica.resumo_backtest = backtest.simular(hist, PoliticaParams.model_validate(politica.params))
    db.execute(update(Politica).where(Politica.ativa).values(ativa=False))
    politica.ativa = True
    politica.publicada_em = agora()
    db.commit()
    db.refresh(politica)
    return politica


@router.post("/internal/reload-historico")
def reload_historico(
    request: Request, db: Db,
    x_internal_token: Annotated[str | None, Header()] = None,
) -> dict[str, int]:
    """Chamado pelo CLI após `load-historico`. Aceita o SECRET_KEY no header ou sessão de gestor."""
    autorizado = bool(x_internal_token) and hmac.compare_digest(x_internal_token or "", settings.secret_key)
    if not autorizado and usuario_atual(request, db).papel != "gestor":
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Acesso restrito.")
    plugins.recarregar(request.app)
    hist = request.app.state.historico
    return {"historico_linhas": 0 if hist is None else len(hist)}
