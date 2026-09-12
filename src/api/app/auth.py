"""Sessão por cookie HttpOnly assinado (itsdangerous), 12 h. Senhas com bcrypt."""

from __future__ import annotations

from typing import Annotated

import bcrypt
from fastapi import Depends, HTTPException, Request, Response, status
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.models import Usuario

COOKIE = "sessao"
_serializer = URLSafeTimedSerializer(settings.secret_key, salt="sessao-v1")


def hash_senha(senha: str) -> str:
    return bcrypt.hashpw(senha.encode("utf-8")[:72], bcrypt.gensalt(rounds=10)).decode("ascii")


def verificar_senha(senha: str, senha_hash: str) -> bool:
    try:
        return bcrypt.checkpw(senha.encode("utf-8")[:72], senha_hash.encode("ascii"))
    except ValueError:
        return False


def criar_token(usuario_id: int) -> str:
    return _serializer.dumps({"uid": usuario_id})


def ler_token(token: str) -> int | None:
    try:
        dados = _serializer.loads(token, max_age=settings.sessao_horas * 3600)
    except (BadSignature, SignatureExpired):
        return None
    uid = dados.get("uid") if isinstance(dados, dict) else None
    return int(uid) if isinstance(uid, int) else None


def definir_cookie(response: Response, usuario_id: int) -> None:
    response.set_cookie(
        COOKIE,
        criar_token(usuario_id),
        max_age=settings.sessao_horas * 3600,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
        path="/",
    )


def limpar_cookie(response: Response) -> None:
    response.delete_cookie(COOKIE, path="/")


def usuario_atual(request: Request, db: Annotated[Session, Depends(get_db)]) -> Usuario:
    token = request.cookies.get(COOKIE)
    uid = ler_token(token) if token else None
    usuario = db.get(Usuario, uid) if uid else None
    if usuario is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Faça login para continuar.")
    return usuario


UsuarioLogado = Annotated[Usuario, Depends(usuario_atual)]


def exigir_gestor(usuario: UsuarioLogado) -> Usuario:
    if usuario.papel != "gestor":
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Acesso restrito ao gestor do banco.")
    return usuario


Gestor = Annotated[Usuario, Depends(exigir_gestor)]


def pode_ver_processo(usuario: Usuario, escritorio_id: int) -> bool:
    return usuario.papel == "gestor" or usuario.escritorio_id == escritorio_id
