import json
from datetime import UTC, datetime

import pytest

from extractor import __main__ as cli
from extractor.leitura import ErroLeitura
from extractor.resumo import ResumoDocumento

RESUMO = ResumoDocumento(
    arquivo="peticao.pdf",
    paginas=3,
    tipo_pdf="mixed",
    paginas_ocr=[2],
    paginas_sem_texto=[3],
    modelo="gpt-teste",
    resumo="Autora idosa nega o empréstimo e pede danos morais.",
    pontos_principais=["Empréstimo de R$ 5.000,00 (p. 1)", "Procuração assinada (p. 2)"],
    gerado_em=datetime(2026, 9, 12, tzinfo=UTC),
)


def test_saida_em_texto(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(cli, "resumir_pdf", lambda pdf, modelo=None: RESUMO)

    assert cli.main(["peticao.pdf"]) == 0

    saida = capsys.readouterr().out
    assert saida.startswith("# peticao.pdf")
    assert "OCR nas páginas: 2" in saida
    assert "sem texto nas páginas 3" in saida
    assert "- Empréstimo de R$ 5.000,00 (p. 1)" in saida


def test_saida_em_json(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(cli, "resumir_pdf", lambda pdf, modelo=None: RESUMO)

    assert cli.main(["peticao.pdf", "--json"]) == 0

    dados = json.loads(capsys.readouterr().out)
    assert dados["paginas_ocr"] == [2]
    assert dados["pontos_principais"] == RESUMO.pontos_principais


def test_erro_de_leitura_sai_com_codigo_1(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def falha(pdf: str, modelo: str | None = None) -> ResumoDocumento:
        raise ErroLeitura("arquivo não encontrado: x.pdf")

    monkeypatch.setattr(cli, "resumir_pdf", falha)

    assert cli.main(["x.pdf"]) == 1
    assert "erro: arquivo não encontrado: x.pdf" in capsys.readouterr().err
