"""Link mágico para a banca: /api/demo?t=<DEMO_TOKEN> loga o advogado da Banca Demo,
reserva um caso livre por 15 minutos e redireciona para ele. Sem senha, sem digitação."""

from __future__ import annotations

import hmac
import time
from collections import defaultdict, deque
from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy import exists, or_, select
from sqlalchemy.orm import Session

from app.auth import definir_cookie
from app.config import settings
from app.db import get_db
from app.models import Decisao, Escritorio, Processo, Usuario
from app.services.recomendacao import agora, registrar_evento
from app.services.seed import EMAIL_DEMO, ESCRITORIO_DEMO

router = APIRouter(tags=["demo"])
RESERVA = timedelta(minutes=15)
LIMITE_POR_MINUTO = 20
_acessos: dict[str, deque[float]] = defaultdict(deque)


def _rate_limit(ip: str) -> None:
    fila = _acessos[ip]
    agora_s = time.monotonic()
    while fila and agora_s - fila[0] > 60:
        fila.popleft()
    if len(fila) >= LIMITE_POR_MINUTO:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS,
                            detail="Muitas tentativas. Aguarde um minuto.")
    fila.append(agora_s)


@router.get("/demo")
def demo(request: Request, t: str, db: Annotated[Session, Depends(get_db)]) -> RedirectResponse:
    _rate_limit(request.client.host if request.client else "?")
    if not hmac.compare_digest(t, settings.demo_token):
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Link de demonstração inválido.")
    usuario = db.scalar(select(Usuario).where(Usuario.email == EMAIL_DEMO))
    banca = db.scalar(select(Escritorio).where(Escritorio.nome == ESCRITORIO_DEMO))
    if usuario is None or banca is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail="Demo não configurada.")

    agora_dt = agora()
    livre = db.scalar(
        select(Processo)
        .where(Processo.escritorio_id == banca.id, Processo.status == "pendente",
               or_(Processo.reservado_ate.is_(None), Processo.reservado_ate < agora_dt),
               ~exists().where(Decisao.processo_id == Processo.id))
        .order_by(Processo.id).limit(1).with_for_update(skip_locked=True, of=Processo)
    )
    if livre is not None:
        livre.reservado_ate = agora_dt + RESERVA
        registrar_evento(db, usuario.id, livre.id, "demo_reservou", {"ip": request.client.host if request.client else None}, commit=False)
        db.commit()
        destino = f"/casos/{livre.id}"
    else:
        destino = "/casos"
    resposta = RedirectResponse(destino, status_code=status.HTTP_303_SEE_OTHER)
    definir_cookie(resposta, usuario.id)
    return resposta
