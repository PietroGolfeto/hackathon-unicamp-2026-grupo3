"""Utilitários pequenos compartilhados."""

from __future__ import annotations

import json
from typing import Any

CASAS_DECIMAIS = 6


def arredondar_floats(obj: Any, casas: int = CASAS_DECIMAIS) -> Any:
    """Arredonda todos os floats de uma estrutura aninhada (legibilidade dos JSONs versionados)."""
    if isinstance(obj, float):
        return round(obj, casas)
    if isinstance(obj, dict):
        return {k: arredondar_floats(v, casas) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [arredondar_floats(v, casas) for v in obj]
    if hasattr(obj, "item"):  # escalares numpy
        return arredondar_floats(obj.item(), casas)
    return obj


def json_dumps(obj: Any, **kw: Any) -> str:
    kw.setdefault("ensure_ascii", False)
    kw.setdefault("indent", 1)
    return json.dumps(arredondar_floats(obj), **kw)
