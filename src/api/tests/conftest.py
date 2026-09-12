"""Testes da API contra um Postgres real (DATABASE_URL; padrão enter_test em localhost).

Sem banco acessível os testes são pulados com aviso. A CI sobe um Postgres 16 de serviço.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

DADOS = Path(__file__).parent / "dados"
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://enter:enter@localhost:5432/enter_test")
os.environ["SECRET_KEY"] = "teste-secreto"
os.environ["DEMO_TOKEN"] = "token-demo"
os.environ["DATA_DIR"] = str(DADOS)
os.environ["DOMAIN"] = ":8080"
os.environ["MODEL_IMPL"] = "nao.existe:Modelo"
os.environ["EXTRACTOR_IMPL"] = "nao.existe:Extrator"

SENHA = "senha123"


@pytest.fixture(scope="session")
def app_pronto():
    from app.db import Base, engine
    from app.main import app  # registra os modelos em Base.metadata antes do drop_all

    try:
        garantir_banco(engine.url)
        with engine.connect() as conn:
            conn.execute(text("select 1"))
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"Postgres indisponível em DATABASE_URL ({exc}); testes da API pulados")
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    with TestClient(app):
        yield app


def garantir_banco(url) -> None:
    """Cria o banco de teste se não existir (conecta ao banco `postgres` do mesmo servidor)."""
    from sqlalchemy import create_engine

    admin = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        existe = conn.execute(text("SELECT 1 FROM pg_database WHERE datname = :n"), {"n": url.database}).scalar()
        if not existe:
            conn.execute(text(f'CREATE DATABASE "{url.database}"'))
    admin.dispose()


def logar(app, email: str) -> TestClient:
    cliente = TestClient(app)
    r = cliente.post("/api/auth/login", json={"email": email, "senha": SENHA})
    assert r.status_code == 200, r.text
    return cliente


@pytest.fixture(scope="session")
def anon(app_pronto) -> TestClient:
    return TestClient(app_pronto)


@pytest.fixture(scope="session")
def adv(app_pronto) -> TestClient:
    return logar(app_pronto, "adv1@escritorio-a")


@pytest.fixture(scope="session")
def adv_b(app_pronto) -> TestClient:
    return logar(app_pronto, "adv1@escritorio-b")


@pytest.fixture(scope="session")
def gestor(app_pronto) -> TestClient:
    return logar(app_pronto, "gestor@banco-ufmg")


@pytest.fixture(scope="session")
def exemplos(app_pronto) -> dict[str, int]:
    """Ingere as duas pastas de tests/dados/exemplos no Escritório A. {numero: id}."""
    from sqlalchemy import select

    from app.db import SessionLocal
    from app.models import Escritorio
    from app.services import ingest

    with SessionLocal() as db:
        esc = db.scalar(select(Escritorio).where(Escritorio.nome == "Escritório A"))
        processos = ingest.ingerir_todos(db, DADOS, app_pronto.state.extrator,
                                         app_pronto.state.modelo, esc.id)
        return {p.numero: p.id for p in processos}
