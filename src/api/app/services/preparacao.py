"""Prepara os casos de data/exemplos/ para a tela do advogado, em duas fases.

Fase 1 (`preparar_base`), síncrona e sem LLM: cria os processos com o que os nomes dos arquivos e o
número CNJ já dizem — documentos, flags de subsídio, UF e scores. Leva milissegundos, então a lista
carrega na hora e ninguém espera por ela.

Fase 2, em background: leitura dos PDFs pelo LLM (P3) e a recomendação sob a política ativa, que na
primeira vez leva dezenas de segundos por caso. O front acompanha por poll (decisão 14, sem
websocket) e só a parte do caso que depende dessa leitura fica esperando. Uma execução por vez: a
API roda com 1 worker, então um lock de módulo basta. Abrir um caso que ainda não foi lido o
manda para a frente da fila (`priorizar`), para o advogado nunca esperar a fila inteira.

Idempotente. O que já está gravado no banco não roda de novo, e o cache do extractor em disco cobre
o resto: a partir da segunda vez nenhuma chamada de LLM acontece.
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
_inicio_lock = threading.Lock()  # serializa `iniciar`: uma fase 1 e uma thread de fase 2 por vez
_fila: list[Path] = []  # o que a fase 2 ainda vai ler, na ordem; `priorizar` reordena
_falhas: dict[str, str] = {}  # numero → erro; caso que falhou não fica "preparando" para sempre
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
    numeros = {ingest.numero_da_pasta(p): p for p in pastas}
    existentes = {
        p.numero: p for p in db.scalars(select(Processo).where(Processo.numero.in_(numeros)))
    }
    return [pasta for numero, pasta in numeros.items()
            if not _pronto(existentes.get(numero), com_extrator)]


def status(db: Session, com_extrator: bool) -> dict[str, Any]:
    with _lock:
        atual = dict(_estado)
    if atual["status"] == RODANDO:
        return atual
    total = len(list(ingest.pastas_de_exemplo(settings.data_dir)))
    falta = len(pendentes(db, com_extrator))
    return _marcar(status=PRONTO if total and not falta else atual["status"],
                   total=total, prontos=total - falta, atual=None)


def extracao_pendente(processo: Processo, com_extrator: bool) -> bool:
    """A leitura dos documentos desse processo ainda vai chegar?

    O front usa isso para mostrar loading só no resumo e na recomendação, deixando o resto do caso
    utilizável. Vale apenas para os casos de `data/exemplos/`: processo sintético não tem autos
    para ler, e sem P3 plugado nada seria inferido de qualquer forma (decisão 27).
    """
    if not com_extrator or processo.origem != "exemplo" or processo.dados_extraidos is not None:
        return False
    with _lock:
        return processo.numero not in _falhas


def preparar_base(app: Any, escritorio_id: int) -> None:
    """Fase 1, síncrona: os processos passam a existir com documentos, subsídios, UF e scores."""
    com_extrator = app.state.extrator is not None
    with SessionLocal() as db:
        politica = svc.politica_ativa(db)
        for pasta in ingest.pastas_de_exemplo(settings.data_dir):
            try:
                processo = ingest.ingerir_base(db, pasta, settings.data_dir, app.state.modelo,
                                               escritorio_id)
            except Exception:
                log.exception("base falhou em %s", pasta.name)
                db.rollback()
                continue
            # sem P3 a leitura não vem; a recomendação já é a definitiva e a lista pode mostrá-la
            if _pronto(processo, com_extrator):
                svc.obter_ou_criar(db, processo, None, politica, app.state.modelo)


def iniciar(app: Any, escritorio_id: int) -> dict[str, Any]:
    """Fase 1 aqui mesmo, fase 2 em thread. Chamada repetida não abre uma segunda thread."""
    with _inicio_lock:
        com_extrator = app.state.extrator is not None
        with _lock:
            rodando = _estado["status"] == RODANDO
        if rodando:  # a fase 1 já passou e a thread está gravando extração: não reescrever a base
            with SessionLocal() as db:
                return status(db, com_extrator)
        preparar_base(app, escritorio_id)
        with SessionLocal() as db:
            atual = status(db, com_extrator)
            falta = pendentes(db, com_extrator)
        if not falta:
            return _marcar(status=PRONTO, erro=None, atual=None)
        prontos = atual["total"] - len(falta)
        with _lock:
            _fila[:] = falta
            _falhas.clear()
        _marcar(status=RODANDO, total=atual["total"], prontos=prontos, atual=None, erro=None)
        threading.Thread(target=_rodar, args=(app, escritorio_id, prontos),
                         name="preparacao", daemon=True).start()
        with _lock:
            return dict(_estado)


def priorizar(numero: str) -> None:
    """Advogado abriu um caso que a fila ainda não leu: ele passa para a frente."""
    with _lock:
        for i, pasta in enumerate(_fila):
            if ingest.numero_da_pasta(pasta) == numero:
                if i:
                    _fila.insert(0, _fila.pop(i))
                return


def _proxima() -> Path | None:
    with _lock:
        return _fila.pop(0) if _fila else None


def _rodar(app: Any, escritorio_id: int, prontos: int) -> None:
    erros: list[str] = []
    try:
        with SessionLocal() as db:
            politica = svc.politica_ativa(db)
            while (pasta := _proxima()) is not None:
                _marcar(atual=pasta.name)
                try:
                    processo = ingest.ingerir_pasta(db, pasta, settings.data_dir,
                                                    app.state.extrator, app.state.modelo,
                                                    escritorio_id)
                    # a recomendação nasce aqui para a lista já vir com ela preenchida
                    svc.obter_ou_criar(db, processo, None, politica, app.state.modelo)
                except Exception as exc:
                    log.exception("preparação falhou em %s", pasta.name)
                    db.rollback()
                    erros.append(f"{pasta.name}: {exc}")
                    with _lock:
                        _falhas[ingest.numero_da_pasta(pasta)] = str(exc)[:200]
                prontos += 1
                _marcar(prontos=prontos)
    except Exception as exc:
        log.exception("preparação interrompida")
        erros.append(str(exc))
    _marcar(status=ERRO if erros else PRONTO, atual=None,
            erro="; ".join(erros)[:500] if erros else None)
