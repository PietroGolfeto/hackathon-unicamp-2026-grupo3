"""Leitura de PDF com pdf-inspector: texto nativo por página e OCR só nas páginas escaneadas."""

from __future__ import annotations

import glob
import importlib.util
import logging
import os
from pathlib import Path

import pdf_inspector
from pydantic import BaseModel, Field

log = logging.getLogger(__name__)

# variável lida pelo pdf-inspector → (pacote que traz a lib nativa, subpasta, padrão do arquivo)
_RUNTIMES_OCR: tuple[tuple[str, str, str, str], ...] = (
    ("PDFIUM_LIB_PATH", "pypdfium2_raw", "", "libpdfium.*"),
    ("ORT_DYLIB_PATH", "onnxruntime", "capi", "libonnxruntime.*"),
)


class ErroLeitura(Exception):
    """Falha ao ler o PDF, com mensagem legível pelo usuário."""


class TextoPdf(BaseModel):
    markdown: str
    paginas: int
    tipo_pdf: str  # text_based, scanned, image_based, mixed
    paginas_ocr: list[int] = Field(default_factory=list)
    paginas_sem_texto: list[int] = Field(default_factory=list)


def _configurar_runtime_ocr() -> None:
    """Aponta o OCR para as libs dos wheels pypdfium2 e onnxruntime, sem sobrescrever o env."""
    for variavel, pacote, subpasta, padrao in _RUNTIMES_OCR:
        if os.environ.get(variavel):
            continue
        spec = importlib.util.find_spec(pacote)
        if spec is None or not spec.submodule_search_locations:
            continue
        pasta = Path(next(iter(spec.submodule_search_locations))) / subpasta
        libs = sorted(glob.glob(str(pasta / padrao)), key=len)
        if libs:
            os.environ[variavel] = libs[0]


def _aplicar_ocr(caminho: Path, paginas: list[int], textos: dict[int, str]) -> tuple[list[int], str]:
    """OCR nas páginas indicadas, trocando o texto delas. Devolve (páginas lidas, motivo da falha)."""
    _configurar_runtime_ocr()
    try:
        resultado = pdf_inspector.process_pdf_with_ocr(str(caminho), page_numbers=paginas)
    except ValueError as exc:
        log.warning("OCR indisponível para %s: %s", caminho.name, exc)
        return [], str(exc)
    lidas = []
    for pagina in resultado.pages:
        if pagina.provenance.source == "ocr" and pagina.markdown.strip():
            textos[pagina.page_number] = pagina.markdown.strip()
            lidas.append(pagina.page_number)
    return sorted(lidas), ""


def ler_pdf(caminho: Path | str) -> TextoPdf:
    """Markdown do PDF com cada página rotulada `[página N]`; OCR onde não há texto nativo."""
    caminho = Path(caminho)
    if not caminho.is_file():
        raise ErroLeitura(f"arquivo não encontrado: {caminho}")
    try:
        info = pdf_inspector.process_pdf(str(caminho))
        extracao = pdf_inspector.extract_pages_markdown(str(caminho))
    except ValueError as exc:
        raise ErroLeitura(f"não foi possível ler {caminho.name}: {exc}") from exc

    textos = {p.page + 1: p.markdown.strip() for p in extracao.pages}  # page vem 0-based
    paginas_ocr, motivo = [], ""
    if info.pages_needing_ocr:
        paginas_ocr, motivo = _aplicar_ocr(caminho, sorted(info.pages_needing_ocr), textos)

    if not any(textos.values()):
        detalhe = f"; OCR indisponível: {motivo}" if motivo else ""
        raise ErroLeitura(f"nenhum texto encontrado em {caminho.name}{detalhe}")

    return TextoPdf(
        markdown="\n\n".join(f"[página {n}]\n{t}" for n, t in sorted(textos.items()) if t),
        paginas=info.page_count,
        tipo_pdf=info.pdf_type,
        paginas_ocr=paginas_ocr,
        paginas_sem_texto=[n for n in range(1, info.page_count + 1) if not textos.get(n)],
    )
