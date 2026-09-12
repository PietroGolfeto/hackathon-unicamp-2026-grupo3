"""Jobs de carga: python -m app.cli <seed|load-historico|ingest|seed-demo|reset-demo|reset>."""

from __future__ import annotations

import argparse
import json
import logging
import sys
import urllib.error
import urllib.request
from pathlib import Path

from sqlalchemy import select

from app import plugins
from app.config import settings
from app.db import Base, SessionLocal, engine
from app.models import Escritorio
from app.services import historico, ingest, seed, seed_demo

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("cli")


def cmd_seed() -> None:
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        seed.rodar(db)


def cmd_load_historico() -> None:
    Base.metadata.create_all(engine)
    df = historico.montar(settings.data_dir)
    n = historico.gravar(engine, df)
    print(f"histórico: {n} linhas (scores {df['scores_origem'].iloc[0]})")
    avisar_api()


def _modelo():
    return plugins.carregar_modelo(historico.carregar_cache(engine))


def cmd_ingest(escritorio: str) -> None:
    Base.metadata.create_all(engine)
    modelo, extrator = _modelo(), plugins.carregar_extrator()
    with SessionLocal() as db:
        seed.rodar(db)
        esc = db.scalar(select(Escritorio).where(Escritorio.nome == escritorio))
        if esc is None:
            sys.exit(f"escritório '{escritorio}' não existe")
        processos = ingest.ingerir_todos(db, settings.data_dir, extrator, modelo, esc.id)
    print(f"ingest: {len(processos)} processos de {settings.exemplos_dir}")


def cmd_seed_demo(csv: Path | None) -> None:
    Base.metadata.create_all(engine)
    caminho = csv or settings.exemplos_dir / "sinteticos_processos.csv"
    if not caminho.exists():
        sys.exit(f"{caminho} não encontrado")
    modelo = _modelo()
    with SessionLocal() as db:
        seed.rodar(db)
        resumo = seed_demo.rodar(db, caminho, modelo)
    print(f"seed-demo: {resumo}")


def cmd_reset_demo() -> None:
    with SessionLocal() as db:
        seed_demo.reset_demo(db)
    print("reset-demo: decisões, eventos e recomendações apagados; processos e políticas mantidos")


def cmd_reset(sem_historico: bool) -> None:
    if "@db:" not in settings.database_url and "localhost" not in settings.database_url \
            and "127.0.0.1" not in settings.database_url:
        sys.exit("reset só roda contra banco local (DATABASE_URL aponta para fora)")
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    cmd_seed()
    if not sem_historico and historico.localizar_csvs(settings.data_dir):
        cmd_load_historico()
    else:
        log.warning("sem CSVs da Enter em %s: histórico vazio, simulação desabilitada", settings.data_dir)
    cmd_ingest("Escritório A")
    cmd_seed_demo(None)
    avisar_api()


def avisar_api() -> None:
    """Pede à API rodando para recarregar o cache; silencioso se ela não estiver de pé."""
    req = urllib.request.Request(
        f"{settings.api_url}/api/internal/reload-historico", method="POST",
        headers={"X-Internal-Token": settings.secret_key},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            print("API recarregou:", json.loads(resp.read()))
    except (urllib.error.URLError, OSError, ValueError) as exc:
        log.info("API não avisada (%s); ela recarrega no próximo start", exc)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("seed", help="escritórios, usuários e política v1 (idempotente)")
    sub.add_parser("load-historico", help="2 CSVs da Enter → historico_sentencas")
    p_ing = sub.add_parser("ingest", help="pastas data/exemplos/<numero>/ → processos")
    p_ing.add_argument("--escritorio", default="Escritório A")
    p_sd = sub.add_parser("seed-demo", help="processos sintéticos + decisões simuladas")
    p_sd.add_argument("--csv", type=Path, default=None)
    sub.add_parser("reset-demo", help="apaga decisões/eventos/recomendações")
    p_rs = sub.add_parser("reset", help="recria o banco e roda tudo (só local)")
    p_rs.add_argument("--sem-historico", action="store_true")
    args = parser.parse_args(argv)
    match args.cmd:
        case "seed":
            cmd_seed()
        case "load-historico":
            cmd_load_historico()
        case "ingest":
            cmd_ingest(args.escritorio)
        case "seed-demo":
            cmd_seed_demo(args.csv)
        case "reset-demo":
            cmd_reset_demo()
        case "reset":
            cmd_reset(args.sem_historico)


if __name__ == "__main__":
    main()
