from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from extractor import leitura
from extractor.leitura import ErroLeitura, ler_pdf


def _ocr_devolvendo(texto: str, chamadas: list[list[int]]) -> Any:
    def ocr_falso(caminho: str, *, page_numbers: list[int]) -> SimpleNamespace:
        chamadas.append(page_numbers)
        pagina = SimpleNamespace(
            page_number=page_numbers[0], markdown=texto, provenance=SimpleNamespace(source="ocr")
        )
        return SimpleNamespace(pages=[pagina])

    return ocr_falso


def test_pdf_de_texto_sai_rotulado_por_pagina_sem_ocr(
    peticao_pdf: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    chamadas: list[list[int]] = []
    monkeypatch.setattr(leitura.pdf_inspector, "process_pdf_with_ocr", _ocr_devolvendo("x", chamadas))

    t = ler_pdf(peticao_pdf)

    assert t.tipo_pdf == "text_based"
    assert t.paginas == 2
    assert t.markdown.startswith("[página 1]\nPETICAO INICIAL")
    assert "[página 2]\nA autora nao reconhece o emprestimo consignado de R$ 5.000,00." in t.markdown
    assert t.paginas_ocr == [] and t.paginas_sem_texto == []
    assert chamadas == []


def test_pagina_escaneada_passa_pelo_ocr(escaneado_pdf: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    chamadas: list[list[int]] = []
    ocr = _ocr_devolvendo("PROCURACAO AD JUDICIA", chamadas)
    monkeypatch.setattr(leitura.pdf_inspector, "process_pdf_with_ocr", ocr)

    t = ler_pdf(escaneado_pdf)

    assert chamadas == [[1]]
    assert t.tipo_pdf == "scanned"
    assert t.paginas_ocr == [1]
    assert t.paginas_sem_texto == []
    assert t.markdown == "[página 1]\nPROCURACAO AD JUDICIA"


def test_sem_runtime_de_ocr_e_sem_texto_explica_o_motivo(
    escaneado_pdf: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def ocr_indisponivel(caminho: str, *, page_numbers: list[int]) -> None:
        raise ValueError("failed to load PDFium")

    monkeypatch.setattr(leitura.pdf_inspector, "process_pdf_with_ocr", ocr_indisponivel)

    with pytest.raises(ErroLeitura, match="OCR indisponível: failed to load PDFium"):
        ler_pdf(escaneado_pdf)


def test_arquivo_inexistente(tmp_path: Path) -> None:
    with pytest.raises(ErroLeitura, match="arquivo não encontrado"):
        ler_pdf(tmp_path / "nao_existe.pdf")


def test_arquivo_que_nao_e_pdf(tmp_path: Path) -> None:
    falso = tmp_path / "falso.pdf"
    falso.write_text("isto não é um PDF")

    with pytest.raises(ErroLeitura, match="não foi possível ler falso.pdf"):
        ler_pdf(falso)


def test_runtime_de_ocr_respeita_o_env_e_acha_as_libs_dos_wheels(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PDFIUM_LIB_PATH", "/minha/libpdfium.so")
    monkeypatch.delenv("ORT_DYLIB_PATH", raising=False)

    leitura._configurar_runtime_ocr()

    assert leitura.os.environ["PDFIUM_LIB_PATH"] == "/minha/libpdfium.so"
    assert Path(leitura.os.environ["ORT_DYLIB_PATH"]).name.startswith("libonnxruntime.")
