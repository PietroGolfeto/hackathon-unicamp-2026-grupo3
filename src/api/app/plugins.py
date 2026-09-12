"""Escolhe a implementação real (P1/P3) por env.

MODEL_IMPL=app.modelo_enteros:ModeloEnteros · EXTRACTOR_IMPL=extractor.pipeline:Extrator
A classe precisa ser instanciável sem argumentos. Falha vira log alto, não erro: o modelo cai no
StubModelo (a UI mostra o badge "stub" pelo campo `origem`); a extração fica desligada (None) e o
portal mostra só o que é determinístico: flags dos subsídios, scores e recomendação (decisão 27).
"""

from __future__ import annotations

import importlib
import logging
from typing import Any

import pandas as pd
from core.docs import ExtratorDocs
from core.modelo import ModeloScores

from app.config import settings
from app.stubs import StubModelo

log = logging.getLogger(__name__)


def _instanciar(spec: str) -> Any:
    modulo, sep, attr = spec.partition(":")
    if not sep or not modulo or not attr:
        raise ValueError(f"spec inválida '{spec}'; use 'pacote.modulo:Classe'")
    return getattr(importlib.import_module(modulo), attr)()


def carregar_modelo(historico: pd.DataFrame | None) -> ModeloScores:
    try:
        modelo = _instanciar(settings.model_impl)
        log.info("modelo real carregado: %s (%s)", settings.model_impl, modelo.info().versao)
        return modelo
    except Exception as exc:  # noqa: BLE001 - qualquer falha de P1 cai no stub
        log.warning("MODEL_IMPL=%s indisponível (%s); usando StubModelo", settings.model_impl, exc)
        return StubModelo(historico)


def carregar_extrator() -> ExtratorDocs | None:
    """Extrator de P3 ou None. Sem P3 não há extração: nada é inferido dos documentos."""
    try:
        extrator = _instanciar(settings.extractor_impl)
        log.info("extrator real carregado: %s", settings.extractor_impl)
        return extrator
    except Exception as exc:  # noqa: BLE001
        log.warning(
            "EXTRACTOR_IMPL=%s indisponível (%s); sem extração de documentos",
            settings.extractor_impl, exc,
        )
        return None


def recarregar(app: Any) -> None:
    """Recarrega o cache do histórico e reconstrói o modelo (o stub depende do histórico)."""
    from app.db import engine
    from app.services import historico

    app.state.historico = historico.carregar_cache(engine)
    app.state.modelo = carregar_modelo(app.state.historico)
    n = 0 if app.state.historico is None else len(app.state.historico)
    log.info("histórico em cache: %d linhas; modelo %s", n, app.state.modelo.info().versao)
