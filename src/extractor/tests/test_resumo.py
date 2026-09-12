from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from extractor import resumo
from extractor.resumo import ErroResumo, ResumoDocumento, _SaidaLLM, resumir_pdf, resumir_texto


class ClienteFalso:
    """Imita `OpenAI().responses.parse` e guarda os argumentos da chamada."""

    def __init__(self, saida: _SaidaLLM | None) -> None:
        self.chamadas: list[dict[str, Any]] = []
        self.responses = SimpleNamespace(parse=self._parse)
        self._saida = saida

    def _parse(self, **kwargs: Any) -> SimpleNamespace:
        self.chamadas.append(kwargs)
        return SimpleNamespace(output_parsed=self._saida)


SAIDA = _SaidaLLM(
    resumo="Petição de autora idosa que nega o empréstimo e pede danos morais.",
    pontos_principais=["Autora de 72 anos (p. 1)", "Empréstimo de R$ 5.000,00 (p. 2)"],
)


def test_resumir_pdf_envia_texto_das_paginas_e_monta_resumo(peticao_pdf: Path) -> None:
    cliente = ClienteFalso(SAIDA)

    r = resumir_pdf(peticao_pdf, client=cliente, modelo="gpt-teste")

    assert isinstance(r, ResumoDocumento)
    assert r.arquivo == "peticao_inicial.pdf"
    assert r.paginas == 2
    assert r.modelo == "gpt-teste"
    assert r.pontos_principais == SAIDA.pontos_principais
    assert not r.texto_truncado
    chamada = cliente.chamadas[0]
    assert chamada["model"] == "gpt-teste"
    assert chamada["text_format"] is _SaidaLLM
    assert "R$ 5.000,00" in chamada["input"]
    assert "[página 2]" in chamada["input"]


def test_modelo_vem_do_env_quando_nao_informado(
    peticao_pdf: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("OPENAI_MODEL", "gpt-do-env")
    cliente = ClienteFalso(SAIDA)

    assert resumir_pdf(peticao_pdf, client=cliente).modelo == "gpt-do-env"
    assert cliente.chamadas[0]["model"] == "gpt-do-env"


def test_texto_longo_e_cortado_no_limite(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(resumo, "LIMITE_CARACTERES", 10)
    cliente = ClienteFalso(SAIDA)

    resumir_texto("a" * 50, client=cliente, modelo="m")

    assert cliente.chamadas[0]["input"] == "a" * 10


def test_texto_vazio_nao_chama_a_api() -> None:
    cliente = ClienteFalso(SAIDA)

    with pytest.raises(ErroResumo, match="não tem texto"):
        resumir_texto("  \n", client=cliente, modelo="m")
    assert cliente.chamadas == []


def test_sem_saida_estruturada_vira_erro_legivel() -> None:
    with pytest.raises(ErroResumo, match="não devolveu"):
        resumir_texto("texto", client=ClienteFalso(None), modelo="m")


def test_sem_chave_da_openai_avisa_antes_de_chamar(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(ErroResumo, match="OPENAI_API_KEY"):
        resumir_texto("texto", modelo="m")
