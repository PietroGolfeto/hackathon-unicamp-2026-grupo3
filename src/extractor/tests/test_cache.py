from pathlib import Path

from extractor import cache


def test_chave_estavel_e_sensivel():
    docs = [("autos/a.pdf", "aa"), ("subsidios/b.pdf", "bb")]
    k = cache.chave(docs, "v1", "m", "s")
    assert k == cache.chave(list(reversed(docs)), "v1", "m", "s")
    assert k != cache.chave([("autos/a.pdf", "aX"), ("subsidios/b.pdf", "bb")], "v1", "m", "s")
    assert k != cache.chave(docs, "v2", "m", "s") != cache.chave(docs, "v1", "m2", "s")
    assert k != cache.chave(docs, "v1", "m", "s2")


def test_grava_le_e_aponta_por_numero(tmp_path: Path):
    c = cache.Cache(tmp_path / "cache")
    assert c.ler("abc") is None
    assert c.gravar("abc", {"dados": {"x": 1}}, numero="0001")
    assert c.ler("abc") == {"dados": {"x": 1}}
    assert c.ler_por_numero("0001") == {"dados": {"x": 1}}
    assert c.ler_por_numero("9999") is None
    assert c.limpar() == 2 and c.ler("abc") is None


def test_diretorio_sem_permissao_nao_explode(tmp_path: Path):
    arquivo = tmp_path / "arquivo"
    arquivo.write_text("não sou pasta")
    c = cache.Cache(arquivo)
    assert c.gravar("k", {"a": 1}) is False
    assert c.ler("k") is None


def test_cache_desativado(tmp_path: Path):
    c = cache.Cache(tmp_path, ativo=False)
    assert c.gravar("k", {"a": 1}) is False and c.ler("k") is None


def test_dir_padrao_respeita_env(monkeypatch):
    monkeypatch.setenv("EXTRACTOR_CACHE_DIR", "/tmp/x")
    assert cache.dir_padrao() == Path("/tmp/x")
    monkeypatch.delenv("EXTRACTOR_CACHE_DIR")
    monkeypatch.setenv("DATA_DIR", "/dados")
    assert cache.dir_padrao() == Path("/dados/cache/extractor")
