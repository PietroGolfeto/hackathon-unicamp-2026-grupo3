from pathlib import Path

from ajuda_docs import pdf_minimo

from extractor import texto


def test_lista_autos_e_subsidios(pasta_exemplo: Path):
    arquivos = texto.listar(pasta_exemplo)
    assert [a.name for a in arquivos] == ["peticao_inicial.txt", "comprovante_credito.txt",
                                          "demonstrativo_evolucao_divida.txt", "laudo_referenciado.txt"]
    assert texto.pasta_do_arquivo(arquivos[0], pasta_exemplo) == "autos"
    assert texto.pasta_do_arquivo(arquivos[1], pasta_exemplo) == "subsidios"


def test_pasta_plana_classifica_pelo_nome(tmp_path: Path):
    (tmp_path / "01_Autos_Processo_0001234.txt").write_text("x")
    (tmp_path / "02_Contrato_1.txt").write_text("y")
    (tmp_path / ".oculto.txt").write_text("z")
    (tmp_path / "planilha.xlsx").write_text("w")
    docs = texto.ler_pasta(tmp_path)
    assert [(d.arquivo, d.pasta) for d in docs] == [("01_Autos_Processo_0001234.txt", "autos"),
                                                    ("02_Contrato_1.txt", "subsidios")]


def test_le_pdf_minimo(tmp_path: Path):
    caminho = tmp_path / "subsidios" / "extrato.pdf"
    caminho.parent.mkdir()
    caminho.write_bytes(pdf_minimo("Extrato de conta teste 123"))
    doc = texto.ler(caminho, tmp_path)
    assert doc.leitor in ("pdftotext", "pypdf")
    assert doc.paginas == 1 and doc.pasta == "subsidios" and not doc.erros
    assert "Extrato de conta teste 123" in doc.texto
    assert len(doc.sha256) == 64


def test_txt_e_arquivo_grande(tmp_path: Path):
    t = tmp_path / "autos" / "peticao.txt"
    t.parent.mkdir()
    t.write_text("DOS FATOS", encoding="utf-8")
    assert texto.ler(t, tmp_path).leitor == "txt"
    grande = tmp_path / "autos" / "grande.pdf"
    grande.write_bytes(b"%PDF-1.4\n" + b"0" * (texto.MAX_BYTES + 1))
    doc = texto.ler(grande, tmp_path)
    assert doc.leitor == "nenhum" and "excede" in doc.erros[0]


def test_pdf_ilegivel_nao_explode(tmp_path: Path):
    ruim = tmp_path / "x.pdf"
    ruim.write_bytes(b"isto nao e um pdf")
    doc = texto.ler(ruim, tmp_path)
    assert doc.erros and doc.texto == ""
