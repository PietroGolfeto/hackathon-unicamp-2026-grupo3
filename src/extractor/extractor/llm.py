"""Cliente do LLM: OpenAI com saída estruturada (`responses.parse`) e contagem de tokens.

`ClienteLLM` é o protocolo que o pipeline usa; os testes injetam um dublê. Sem OPENAI_API_KEY,
`cliente_do_ambiente()` devolve None e o pipeline só responde do cache.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any, Protocol

from pydantic import BaseModel

log = logging.getLogger(__name__)
MODELO_PADRAO = "gpt-4o-mini"


class ErroLLM(RuntimeError):
    """Falha ao obter uma resposta estruturada do modelo."""


class ErroConfiguracao(ErroLLM):
    """Falta chave ou configuração para chamar o modelo."""


@dataclass
class Resposta[T: BaseModel]:
    saida: T
    modelo: str
    tokens_entrada: int
    tokens_saida: int


class ClienteLLM(Protocol):
    modelo: str

    def completar[T: BaseModel](self, instrucoes: str, entrada: str, esquema: type[T]) -> Resposta[T]: ...


class ClienteOpenAI:
    def __init__(self, api_key: str | None = None, modelo: str | None = None, timeout: float = 120,
                 tentativas: int = 2) -> None:
        from openai import OpenAI

        chave = (api_key or os.environ.get("OPENAI_API_KEY", "")).strip()
        if not chave:
            raise ErroConfiguracao("OPENAI_API_KEY ausente")
        self.modelo = (modelo or os.environ.get("OPENAI_MODEL", "")).strip() or MODELO_PADRAO
        self._client = OpenAI(api_key=chave, timeout=timeout, max_retries=tentativas)

    def completar[T: BaseModel](self, instrucoes: str, entrada: str, esquema: type[T]) -> Resposta[T]:
        extras: dict[str, Any] = {}
        if self.modelo.startswith(("gpt-5", "o1", "o3", "o4")):
            extras["reasoning"] = {"effort": "low"}  # extração e resumo não precisam de raciocínio longo
        try:
            resp = self._client.responses.parse(
                model=self.modelo, instructions=instrucoes, input=entrada, text_format=esquema, **extras,
            )
        except Exception as exc:  # erro de rede, auth ou API vira ErroLLM legível
            raise ErroLLM(f"falha na OpenAI ({type(exc).__name__}): {exc}") from exc
        saida = resp.output_parsed
        if saida is None:
            raise ErroLLM("resposta sem conteúdo estruturado (recusa ou truncamento)")
        uso = getattr(resp, "usage", None)
        return Resposta(
            saida=saida, modelo=getattr(resp, "model", None) or self.modelo,
            tokens_entrada=int(getattr(uso, "input_tokens", 0) or 0),
            tokens_saida=int(getattr(uso, "output_tokens", 0) or 0),
        )


def cliente_do_ambiente() -> ClienteOpenAI | None:
    try:
        return ClienteOpenAI()
    except ErroConfiguracao as exc:
        log.warning("%s: o extractor responde só do cache", exc)
        return None
