"""Fixtures do pytest; helpers em ajuda.py.

`--llm` liga os testes marcados `llm`, que chamam a OpenAI de verdade (gastam tokens). Sem a opção
eles são pulados; o resumo do que o modelo devolveu sai no fim da sessão.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from ajuda import FakeCliente
from ajuda_docs import PASTA

CHAMADAS_LLM = pytest.StashKey[list[dict]]()


@pytest.fixture
def pasta_exemplo() -> Path:
    return PASTA


@pytest.fixture
def fake() -> FakeCliente:
    return FakeCliente()


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption("--llm", action="store_true", default=False,
                     help="roda os testes que chamam a OpenAI de verdade (precisa de OPENAI_API_KEY)")


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "llm: chama a OpenAI de verdade; só roda com --llm")
    config.stash[CHAMADAS_LLM] = []


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if config.getoption("--llm"):
        return
    pular = pytest.mark.skip(reason="chamada real ao LLM: rode com --llm (make test-llm)")
    for item in items:
        if "llm" in item.keywords:
            item.add_marker(pular)


@pytest.fixture
def registrar_chamada(request: pytest.FixtureRequest):
    """Os testes com LLM entregam aqui o que o modelo devolveu; o resumo sai no fim da sessão."""
    return request.config.stash[CHAMADAS_LLM].append


def pytest_terminal_summary(terminalreporter, exitstatus, config: pytest.Config) -> None:
    chamadas = config.stash.get(CHAMADAS_LLM, [])
    if not chamadas:
        return
    from ajuda_llm import resumo_terminal

    terminalreporter.section("o que o LLM devolveu", sep="=")
    terminalreporter.write_line(resumo_terminal(chamadas))
