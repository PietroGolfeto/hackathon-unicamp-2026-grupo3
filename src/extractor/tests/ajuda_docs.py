"""Ajuda dos testes (parte determinística): pasta sintética e PDFs mínimos escritos à mão."""

from __future__ import annotations

from pathlib import Path

DADOS = Path(__file__).parent / "dados"
NUMERO = "0001234-56.2024.8.13.0001"
PASTA = DADOS / NUMERO


def pdf_minimo(texto: str, javascript: bool = False) -> bytes:
    """Uma página A4 com `texto` em Helvetica (só ASCII). Com `javascript`, catálogo com /OpenAction e /Names."""
    conteudo = f"BT /F1 18 Tf 72 720 Td ({texto}) Tj ET".encode("latin-1")
    catalogo = "<< /Type /Catalog /Pages 2 0 R"
    if javascript:
        catalogo += (" /OpenAction << /S /JavaScript /JS (app.alert\\(1\\)) >>"
                     " /Names << /JavaScript << /Names [(a) 6 0 R] >> >>")
    catalogo += " >>"
    objetos: list[bytes] = [
        catalogo.encode("latin-1"),
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R"
         b" /Resources << /Font << /F1 5 0 R >> >> >>"),
        f"<< /Length {len(conteudo)} >>\nstream\n".encode() + conteudo + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    if javascript:
        objetos.append(b"<< /S /JavaScript /JS (app.alert\\(2\\)) >>")
    saida = bytearray(b"%PDF-1.4\n")
    offsets: list[int] = []
    for i, obj in enumerate(objetos, start=1):
        offsets.append(len(saida))
        saida += f"{i} 0 obj\n".encode() + obj + b"\nendobj\n"
    xref = len(saida)
    saida += f"xref\n0 {len(objetos) + 1}\n0000000000 65535 f \n".encode()
    for off in offsets:
        saida += f"{off:010d} 00000 n \n".encode()
    saida += f"trailer\n<< /Size {len(objetos) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return bytes(saida)
