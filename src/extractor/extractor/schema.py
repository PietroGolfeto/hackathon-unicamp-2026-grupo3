"""Esquema da resposta do LLM (structured outputs em modo estrito).

O modelo devolve só duas listas: `resumo` (até 5 bullets de uma linha, cada um com a fonte entre
colchetes) e `contradicoes` (afirmações de fato da petição desmentidas por prova objetiva de um
subsídio; vazia se não houver). Tudo o mais em `DadosExtraidos` e `Analise` vem de regra, em
`pipeline.py`. Sem defaults nem validações numéricas: o esquema JSON precisa ser aceito pela API.
"""

from __future__ import annotations

import hashlib
import json

from pydantic import BaseModel, ConfigDict


class _Estrito(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SaidaLLM(_Estrito):
    resumo: list[str]
    contradicoes: list[str]


def hash_esquema(modelo: type[BaseModel] = SaidaLLM) -> str:
    """Muda quando o esquema muda; entra na chave do cache."""
    bruto = json.dumps(modelo.model_json_schema(), sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(bruto.encode("utf-8")).hexdigest()[:16]
