"""Chamadas reais à OpenAI sobre os PDFs de docs/Caso_*/: o que o modelo devolve e quanto pesa.

Só roda com `pytest --llm` (ou `make test-llm`); gasta tokens. Cache em pasta temporária, então cada
rodada chama o modelo de novo. O resumo (saída crua, tokens, tamanhos) sai no fim da sessão e o JSON
completo fica em data/cache/testes-llm/<rodada>/.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from ajuda_llm import ESPERADOS, gravar, medir, pasta_da_rodada, pastas_casos
from dotenv import load_dotenv

from extractor.cache import Cache
from extractor.llm import ClienteOpenAI, ErroConfiguracao
from extractor.pipeline import Extrator

pytestmark = pytest.mark.llm


@pytest.fixture(scope="module")
def cliente() -> ClienteOpenAI:
    load_dotenv(Path(__file__).resolve().parents[3] / ".env")
    try:
        return ClienteOpenAI()
    except ErroConfiguracao as exc:
        pytest.skip(str(exc))


@pytest.fixture(scope="module")
def pasta_run() -> Path:
    return pasta_da_rodada()


@pytest.mark.parametrize("pasta", pastas_casos(), ids=lambda p: p.name[:7])
def test_llm_devolve_dados_e_analise(pasta: Path, cliente: ClienteOpenAI, pasta_run: Path, tmp_path: Path,
                                     registrar_chamada):
    ext = Extrator(cliente=cliente, cache=Cache(tmp_path / "cache"))
    prep = ext.preparar(pasta)
    res = ext.processar(pasta)
    medidas = medir(res, prep.ausentes)
    arquivo = gravar(res, medidas, pasta_run)
    registrar_chamada({"medidas": medidas, "saida": res.saida_llm.model_dump(), "arquivo": arquivo})

    assert not res.cache_hit and res.tokens_entrada > 0 and res.tokens_saida > 0
    s = res.saida_llm
    assert s.dados.resumo_fatos.strip() and s.analise.tese_provavel_autor.strip() and s.analise.texto.strip()
    assert 0.0 <= s.dados.confianca <= 1.0
    assert s.dados.autor.nome and s.dados.advogado_autor.nome

    if esperado := ESPERADOS.get(res.numero):  # o que as regras garantem, seja qual for o modelo
        finais = set(res.dados.codigos_sinais())
        assert esperado["obrigatorios"] <= finais, f"faltam sinais: {esperado['obrigatorios'] - finais}"
        assert not (esperado["proibidos"] & finais), f"sinais indevidos: {esperado['proibidos'] & finais}"
        assert res.dados.uf == esperado["uf"] and res.dados.valor_causa == esperado["valor_causa"]
