import json
from pathlib import Path

from extractor import benchmark, parsing


def test_benchmark_roda_sem_llm_e_mede_etapas(pasta_exemplo: Path, tmp_path: Path, capsys):
    saida = tmp_path / "bench.json"
    assert benchmark.main([str(pasta_exemplo), "--repeticoes", "1", "--leitores", "pdftotext", "--stress",
                           "--json", str(saida), "--md", str(tmp_path / "bench.md")]) == 0
    md = capsys.readouterr().out
    for secao in ("## Resumo por processo", "## Tempo por etapa", "## Baselines", "## Stress e escala", "## Integridade"):
        assert secao in md
    res = json.loads(saida.read_text(encoding="utf-8"))
    caso = res["casos"][0]
    assert caso["numero"] == "0001234-56.2024.8.13.0001" and len(caso["docs"]) == 4
    assert caso["paridade_preparar"] and caso["determinista"]  # etapas medidas = Extrator.preparar
    assert set(caso["tempos_ms"]) >= {"leitura", "seguranca", "parsing", "brief", "total"}
    assert caso["fatos"]["recall"]["brief"] == 100.0 and caso["fatos"]["faltando_no_brief"] == []
    assert caso["baselines"]["ingenuo_mesmo_orcamento"]["tokens"] > 0
    assert res["overhead"]["instrucoes"] > 0
    assert all(s["dentro_do_limite"] for s in res["stress"])
    assert all(s["tokens_brief"] < s["tokens_bruto"] for s in res["stress"] if s["chars_bruto"] > 20000)


def test_contador_sem_tiktoken_estima_por_caracteres(monkeypatch):
    import builtins

    real_import = builtins.__import__

    def sem_tiktoken(nome, *a, **k):
        if nome == "tiktoken":
            raise ImportError
        return real_import(nome, *a, **k)

    monkeypatch.setattr(builtins, "__import__", sem_tiktoken)
    tok = benchmark.Contador()
    assert not tok.exato and tok("a" * 400) == 100 and tok("") == 0
    assert tok(parsing.LIMITES["peticao"] * "x") == parsing.LIMITES["peticao"] // 4
