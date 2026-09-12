import zlib
from pathlib import Path

import pytest


def _montar_pdf(objs: list[bytes]) -> bytes:
    """Serializa objetos PDF (numerados a partir de 1, catálogo primeiro) com xref correto."""
    saida = b"%PDF-1.4\n"
    offsets = []
    for i, obj in enumerate(objs, 1):
        offsets.append(len(saida))
        saida += f"{i} 0 obj\n".encode() + obj + b"\nendobj\n"
    xref = len(saida)
    saida += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode()
    saida += "".join(f"{o:010d} 00000 n \n" for o in offsets).encode()
    saida += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return saida


def pdf_de_texto(paginas: list[list[str]]) -> bytes:
    """PDF mínimo e válido com texto nativo, uma lista de linhas por página (Helvetica, ASCII)."""
    n = len(paginas)
    kids = " ".join(f"{3 + 2 * i} 0 R" for i in range(n))
    objs = [b"<< /Type /Catalog /Pages 2 0 R >>", f"<< /Type /Pages /Kids [{kids}] /Count {n} >>".encode()]
    fonte = 3 + 2 * n
    for i, linhas in enumerate(paginas):
        conteudo = "BT /F1 12 Tf 72 720 Td 14 TL "
        conteudo += " ".join(f"({linha}) Tj T*" for linha in linhas) + " ET"
        objs.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents {4 + 2 * i} 0 R "
            f"/Resources << /Font << /F1 {fonte} 0 R >> >> >>".encode()
        )
        objs.append(f"<< /Length {len(conteudo)} >>\nstream\n{conteudo}\nendstream".encode())
    objs.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    return _montar_pdf(objs)


def pdf_escaneado() -> bytes:
    """PDF de uma página só com imagem (sem texto nativo): o pdf-inspector o classifica `scanned`."""
    largura, altura = 400, 100
    pixels = bytes(255 if (x // 20 + y // 20) % 2 else 0 for y in range(altura) for x in range(largura))
    imagem = zlib.compress(pixels)
    conteudo = f"q {largura} 0 0 {altura} 72 600 cm /Im1 Do Q"
    return _montar_pdf([
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
            b"/Resources << /XObject << /Im1 5 0 R >> >> >>"
        ),
        f"<< /Length {len(conteudo)} >>\nstream\n{conteudo}\nendstream".encode(),
        f"<< /Type /XObject /Subtype /Image /Width {largura} /Height {altura} "
        f"/ColorSpace /DeviceGray /BitsPerComponent 8 /Filter /FlateDecode "
        f"/Length {len(imagem)} >>\nstream\n".encode() + imagem + b"\nendstream",
    ])


@pytest.fixture
def peticao_pdf(tmp_path: Path) -> Path:
    caminho = tmp_path / "peticao_inicial.pdf"
    caminho.write_bytes(pdf_de_texto([
        ["PETICAO INICIAL", "Autora: Maria da Silva, 72 anos, aposentada."],
        ["A autora nao reconhece o emprestimo consignado de R$ 5.000,00.", "Pede danos morais."],
    ]))
    return caminho


@pytest.fixture
def escaneado_pdf(tmp_path: Path) -> Path:
    caminho = tmp_path / "procuracao_escaneada.pdf"
    caminho.write_bytes(pdf_escaneado())
    return caminho
