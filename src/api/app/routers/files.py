"""Serve os PDFs dos autos e subsídios. Só arquivos listados em processo.documentos."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.auth import UsuarioLogado
from app.config import settings
from app.db import get_db
from app.routers.processos import obter_processo
from app.services.recomendacao import registrar_evento

router = APIRouter(tags=["files"])


@router.get("/files/{processo_id}/{arquivo}")
def baixar(
    processo_id: int, arquivo: str, usuario: UsuarioLogado, db: Annotated[Session, Depends(get_db)]
) -> FileResponse:
    p = obter_processo(db, processo_id, usuario)
    doc = next((d for d in p.documentos or [] if d.get("arquivo") == arquivo), None)
    if doc is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Documento não encontrado.")
    raiz = settings.data_dir.resolve()
    caminho = (raiz / doc["caminho"]).resolve()
    if raiz not in caminho.parents or not caminho.is_file():
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Arquivo não encontrado no servidor.")
    registrar_evento(db, usuario.id, p.id, "abriu_documento", {"arquivo": arquivo, "tipo": doc["tipo"]})
    return FileResponse(caminho, filename=arquivo, content_disposition_type="inline")
