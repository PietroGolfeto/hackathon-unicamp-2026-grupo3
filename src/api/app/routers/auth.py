from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import UsuarioLogado, definir_cookie, limpar_cookie, verificar_senha
from app.db import get_db
from app.models import Usuario
from app.schemas import LoginIn, UsuarioOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=UsuarioOut)
def login(dados: LoginIn, response: Response, db: Annotated[Session, Depends(get_db)]) -> Usuario:
    usuario = db.scalar(select(Usuario).where(Usuario.email == dados.email.strip().lower()))
    if usuario is None or not verificar_senha(dados.senha, usuario.senha_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="E-mail ou senha inválidos.")
    definir_cookie(response, usuario.id)
    return usuario


@router.get("/me", response_model=UsuarioOut)
def me(usuario: UsuarioLogado) -> Usuario:
    return usuario


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response) -> None:
    limpar_cookie(response)
