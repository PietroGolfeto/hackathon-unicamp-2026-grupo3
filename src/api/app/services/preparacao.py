"""Prepara os casos de data/exemplos/ antes de a lista do advogado carregar.

A tela do advogado só faz sentido com as inferências prontas: extração dos PDFs pelo LLM (P3),
scores do modelo (P1) e a recomendação sob a política ativa. Isso leva dezenas de segundos por
caso na primeira vez, então roda em background e o front acompanha por poll (decisão 14, sem
websocket). Uma execução por vez: a API roda com 1 worker, então um lock de módulo basta.

Idempotente. O que já está gravado no banco não roda de novo, e o cache do extractor em disco
cobre o resto: a partir da segunda vez nenhuma chamada de LLM acontece.
"""

from __future__ import annotations

import logging
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import SessionLocal
from app.models import Processo
from app.services import ingest
from app.services import recomendacao as svc

log = logging.getLogger(__name__)

OCIOSO, RODANDO, PRONTO, ERRO = "ocioso", "rodando", "pronto", "erro"

_lock = threading.Lock()
_estado: dict[str, Any] = {
    "status": OCIOSO, "total": 0, "prontos": 0, "atual": None, "erro": None, "atualizado_em": None,
}


def _marcar(**campos: Any) -> dict[str, Any]:
    with _lock:
        _estado.update(campos, atualizado_em=datetime.now(UTC))
        return dict(_estado)


def _pronto(processo: Processo | None, com_extrator: bool) -> bool:
    """Sem P3 plugado nada é inferido dos documentos (decisão 27) — aí basta o processo existir."""
    if processo is None:
        return False
    if not com_extrator:
        return processo.scores is not None
    return processo.scores is not None and processo.dados_extraidos is not None


def pendentes(db: Session, com_extrator: bool) -> list[Path]:
    pastas = list(ingest.pastas_de_exemplo(settings.data_dir))
    numeros = {p.name: p for p in pastas}
    existentes = {
        p.numero: p for p in db.scalars(select(Processo).where(Processo.numero.in_(numeros)))
    }
    return [pasta for numero, pasta in numeros.items() if not _pronto(existentes.get(numero), com_extrator)]


def status(db: Session, com_extrator: bool) -> dict[str, Any]:
    with _lock:
        atual = dict(_estado)
    if atual["status"] == RODANDO:
        return atual
    total = len(list(ingest.pastas_de_exemplo(settings.data_dir)))
    falta = len(pendentes(db, com_extrator))
    return _marcar(status=PRONTO if total and not falta else atual["status"],
                   total=total, prontos=total - falta, atual=None)


def iniciar(app: Any, escritorio_id: int) -> dict[str, Any]:
    """Dispara a preparação se houver o que fazer. Chamada repetida não abre uma segunda thread."""
    com_extrator = app.state.extrator is not None
    with SessionLocal() as db:
        atual = status(db, com_extrator)
        if atual["status"] == RODANDO:
            return atual
        falta = pendentes(db, com_extrator)
    if not falta:
        return _marcar(status=PRONTO, erro=None, atual=None)
    pronto = atual["total"] - len(falta)
    _marcar(status=RODANDO, total=atual["total"], prontos=pronto, atual=None, erro=None)
    threading.Thread(target=_rodar, args=(app, escritorio_id, falta, pronto),
                     name="preparacao", daemon=True).start()
    with _lock:
        return dict(_estado)


def _rodar(app: Any, escritorio_id: int, pastas: list[Path], prontos: int) -> None:
    erros: list[str] = []
    try:
        with SessionLocal() as db:
            politica = svc.politica_ativa(db)
            for pasta in pastas:
                _marcar(atual=pasta.name)
                try:
                    processo = ingest.ingerir_pasta(db, pasta, settings.data_dir, app.state.extrator,
                                                    app.state.modelo, escritorio_id)
                    # a recomendação nasce aqui para a lista já vir com ela preenchida
                    svc.obter_ou_criar(db, processo, None, politica, app.state.modelo)
                except Exception as exc:
                    log.exception("preparação falhou em %s", pasta.name)
                    db.rollback()
                    erros.append(f"{pasta.name}: {exc}")
                prontos += 1
                _marcar(prontos=prontos)
    except Exception as exc:
        log.exception("preparação interrompida")
        erros.append(str(exc))
    _marcar(status=ERRO if erros else PRONTO, atual=None,
            erro="; ".join(erros)[:500] if erros else None)
