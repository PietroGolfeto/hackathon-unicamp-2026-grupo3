"""App FastAPI. Lifespan: create_all → seed → cache do histórico → plugins de modelo/extrator."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import JSONResponse

from app import plugins
from app.db import Base, SessionLocal, engine
from app.routers import (
    aprovacoes,
    auth,
    dashboard,
    demo,
    files,
    politicas,
    preparacao,
    processos,
)
from app.services import seed

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        seed.rodar(db)
    plugins.recarregar(app)
    app.state.extrator = plugins.carregar_extrator()
    yield


app = FastAPI(
    title="Política de Acordos — Banco UFMG",
    lifespan=lifespan,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    redoc_url=None,
)

api = APIRouter(prefix="/api")


@api.get("/health")
def health(request: Request) -> dict[str, object]:
    hist = request.app.state.historico
    extrator = request.app.state.extrator
    return {
        "ok": True,
        "historico_linhas": 0 if hist is None else len(hist),
        "modelo": request.app.state.modelo.info().versao,
        "extrator": None if extrator is None else type(extrator).__name__,
    }


api.include_router(auth.router)
api.include_router(processos.router)
api.include_router(preparacao.router)
api.include_router(files.router)
api.include_router(politicas.router)
api.include_router(dashboard.router)
api.include_router(aprovacoes.router)
api.include_router(demo.router)
app.include_router(api)


@app.exception_handler(Exception)
async def erro_generico(request: Request, exc: Exception) -> JSONResponse:
    log.exception("erro não tratado em %s", request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Erro interno. Tente novamente."})
