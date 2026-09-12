"""Leitura dos documentos de um processo: PDF (pdftotext do poppler, senão pypdf) e TXT.

Nada aqui interpreta o conteúdo. Só localiza os arquivos, respeita limites de tamanho e páginas
e devolve o texto bruto por documento, com o leitor usado e a pasta de origem (autos/subsidios).
"""

from __future__ import annotations

import logging
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PyPdfError

log = logging.getLogger(__name__)

EXTENSOES = {".pdf", ".txt"}
MAX_BYTES = 20 * 1024 * 1024
MAX_PAGINAS = 200
PASTAS = ("autos", "subsidios")
_PADRAO_AUTOS = re.search  # alias curto para a heurística de nome abaixo


@dataclass
class Documento:
    caminho: Path
    arquivo: str
    pasta: str  # autos | subsidios
    bytes: int
    paginas: int | None = None
    texto: str = ""
    leitor: str = ""  # pdftotext | pypdf | txt | nenhum
    erros: list[str] = field(default_factory=list)
    reader: PdfReader | None = field(default=None, repr=False)

    @property
    def sha256(self) -> str:
        return hash_arquivo(self.caminho)


def hash_arquivo(caminho: Path) -> str:
    import hashlib

    h = hashlib.sha256()
    with caminho.open("rb") as f:
        for bloco in iter(lambda: f.read(1 << 16), b""):
            h.update(bloco)
    return h.hexdigest()


def pasta_do_arquivo(caminho: Path, raiz: Path) -> str:
    """autos/ ou subsidios/ pela subpasta; pasta plana usa o nome (Autos_Processo… → autos)."""
    try:
        primeiro = caminho.relative_to(raiz).parts[0]
    except ValueError:
        primeiro = ""
    if primeiro in PASTAS:
        return primeiro
    nome = caminho.stem.lower()
    if re.search(r"autos|peti[cç][aã]o|inicial|processo", nome):
        return "autos"
    return "subsidios"


def listar(raiz: Path) -> list[Path]:
    """Arquivos .pdf/.txt de autos/ e subsidios/; sem essas subpastas, os da própria pasta."""
    if not raiz.is_dir():
        return []
    pastas = [raiz / p for p in PASTAS if (raiz / p).is_dir()] or [raiz]
    arquivos: list[Path] = []
    for pasta in pastas:
        for arq in sorted(pasta.iterdir()):
            if arq.is_file() and not arq.name.startswith(".") and arq.suffix.lower() in EXTENSOES:
                arquivos.append(arq)
    return arquivos


def _pdftotext_disponivel() -> bool:
    return shutil.which("pdftotext") is not None


def _ler_pdftotext(caminho: Path, paginas: int | None) -> str | None:
    cmd = ["pdftotext", "-layout", "-enc", "UTF-8"]
    if paginas and paginas > MAX_PAGINAS:
        cmd += ["-l", str(MAX_PAGINAS)]
    cmd += [str(caminho), "-"]
    try:
        saida = subprocess.run(cmd, capture_output=True, timeout=60, check=True)
    except (OSError, subprocess.SubprocessError) as exc:
        log.warning("pdftotext falhou em %s (%s); tentando pypdf", caminho.name, exc)
        return None
    return saida.stdout.decode("utf-8", errors="replace")


def _ler_pypdf(reader: PdfReader) -> str:
    partes: list[str] = []
    for i, pagina in enumerate(reader.pages):
        if i >= MAX_PAGINAS:
            break
        try:
            partes.append(pagina.extract_text() or "")
        except Exception as exc:  # noqa: BLE001 - página corrompida não derruba o documento
            partes.append("")
            log.warning("pypdf não leu a página %d: %s", i + 1, exc)
    return "\f".join(partes)


def abrir_pdf(caminho: Path) -> tuple[PdfReader | None, str | None]:
    """PdfReader ou (None, motivo). PDF cifrado com senha vazia é aberto; com senha real, não."""
    try:
        reader = PdfReader(str(caminho))
        if reader.is_encrypted:
            try:
                if not reader.decrypt(""):
                    return None, "PDF cifrado com senha"
            except Exception as exc:  # noqa: BLE001
                return None, f"PDF cifrado ({exc})"
        _ = len(reader.pages)
        return reader, None
    except (PyPdfError, OSError, ValueError, RecursionError) as exc:
        return None, f"PDF ilegível ({exc})"


def ler(caminho: Path, raiz: Path) -> Documento:
    """Lê um arquivo do processo. Erros viram `erros` no documento, nunca exceção."""
    doc = Documento(caminho=caminho, arquivo=caminho.name, pasta=pasta_do_arquivo(caminho, raiz),
                    bytes=caminho.stat().st_size, leitor="nenhum")
    if doc.bytes > MAX_BYTES:
        doc.erros.append(f"arquivo com {doc.bytes / 1e6:.1f} MB excede o limite de {MAX_BYTES / 1e6:.0f} MB")
        return doc
    if caminho.suffix.lower() == ".txt":
        doc.texto = caminho.read_text(encoding="utf-8", errors="replace")
        doc.leitor = "txt"
        return doc

    reader, motivo = abrir_pdf(caminho)
    if reader is None:
        doc.erros.append(motivo or "PDF ilegível")
        return doc
    doc.reader = reader
    doc.paginas = len(reader.pages)
    if doc.paginas > MAX_PAGINAS:
        doc.erros.append(f"{doc.paginas} páginas; lidas só as {MAX_PAGINAS} primeiras")
    texto = _ler_pdftotext(caminho, doc.paginas) if _pdftotext_disponivel() else None
    if texto is not None and texto.strip():
        doc.texto, doc.leitor = texto, "pdftotext"
    else:
        doc.texto, doc.leitor = _ler_pypdf(reader), "pypdf"
    if not doc.texto.strip():
        doc.erros.append("PDF sem camada de texto (digitalizado?); nada extraído")
    return doc


def ler_pasta(raiz: Path) -> list[Documento]:
    return [ler(arq, raiz) for arq in listar(raiz)]
