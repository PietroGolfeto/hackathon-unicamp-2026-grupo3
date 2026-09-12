"""Seed idempotente: escritórios, usuários e a política v1. Upsert por chave natural."""

from __future__ import annotations

import logging

from core.politica import PoliticaParams
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth import hash_senha
from app.models import Escritorio, Politica, Usuario

log = logging.getLogger(__name__)

SENHA_PADRAO = "senha123"
ESCRITORIO_DEMO = "Banca Demo"
EMAIL_DEMO = "demo@banca-demo"

ESCRITORIOS = ["Escritório A", "Escritório B", "Escritório C", ESCRITORIO_DEMO]
USUARIOS: list[tuple[str, str, str, str | None]] = [
    # (nome, email, papel, escritório)
    ("Ana Ribeiro", "adv1@escritorio-a", "advogado", "Escritório A"),
    ("Bruno Castro", "adv2@escritorio-a", "advogado", "Escritório A"),
    ("Carla Nunes", "adv1@escritorio-b", "advogado", "Escritório B"),
    ("Diego Alves", "adv2@escritorio-b", "advogado", "Escritório B"),
    ("Elisa Prado", "adv1@escritorio-c", "advogado", "Escritório C"),
    ("Fábio Lima", "adv2@escritorio-c", "advogado", "Escritório C"),
    ("Advogado da banca", EMAIL_DEMO, "advogado", ESCRITORIO_DEMO),
    ("Gestora Jurídica", "gestor@banco-ufmg", "gestor", None),
]


def rodar(db: Session) -> None:
    escritorios = {e.nome: e for e in db.scalars(select(Escritorio))}
    for nome in ESCRITORIOS:
        if nome not in escritorios:
            escritorios[nome] = Escritorio(nome=nome)
            db.add(escritorios[nome])
    db.flush()

    existentes = {u.email for u in db.scalars(select(Usuario))}
    for nome, email, papel, escritorio in USUARIOS:
        if email in existentes:
            continue
        db.add(
            Usuario(
                nome=nome,
                email=email,
                papel=papel,
                senha_hash=hash_senha(SENHA_PADRAO),
                escritorio_id=escritorios[escritorio].id if escritorio else None,
            )
        )

    if db.scalar(select(func.count()).select_from(Politica)) == 0:
        db.add(
            Politica(
                versao=1,
                nome="Política inicial (defaults do plano)",
                params=PoliticaParams().model_dump(),
                ativa=True,
            )
        )
    db.commit()
    log.info("seed ok: %d escritórios, %d usuários", len(ESCRITORIOS), len(USUARIOS))
