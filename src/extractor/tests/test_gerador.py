"""Casos gerados por ficha: os documentos têm o texto que as regras leem, e a injeção sai do brief."""

from pathlib import Path

import pytest
from ajuda import FakeCliente
from core.docs import subsidios_por_arquivos

from extractor import gerador, texto
from extractor.cache import Cache
from extractor.pipeline import Extrator

# Sinais que cada caso do catálogo tem de produzir por regra, e os que não pode produzir.
ESPERADOS: dict[str, tuple[set[str], set[str]]] = {
    "0912345-67.2024.8.13.0001": (
        {"DOCUMENTO_SUSPEITO"},
        {"IDOSO", "SEM_CONTRATO", "CREDITO_CONTA_TERCEIRO", "LIVENESS_AUSENTE_CANAL_DIGITAL",
         "ASSINATURA_DIVERGENTE", "BOLETIM_OCORRENCIA", "RECLAMACAO_BACEN"},
    ),
    "0945678-12.2024.8.26.0100": (
        {"IDOSO", "BOLETIM_OCORRENCIA", "RECLAMACAO_BACEN", "SEM_CONTRATO", "CREDITO_CONTA_TERCEIRO",
         "LIVENESS_AUSENTE_CANAL_DIGITAL", "DOCUMENTO_SUSPEITO"},
        {"ASSINATURA_DIVERGENTE"},
    ),
    "0923456-78.2024.8.16.0001": (
        {"IDOSO", "BOLETIM_OCORRENCIA", "ASSINATURA_DIVERGENTE"},
        {"DOCUMENTO_SUSPEITO", "SEM_CONTRATO", "CREDITO_CONTA_TERCEIRO", "LIVENESS_AUSENTE_CANAL_DIGITAL",
         "RECLAMACAO_BACEN"},
    ),
}


@pytest.fixture(scope="module")
def catalogo(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Path]:
    raiz = tmp_path_factory.mktemp("catalogo")
    return {f.numero: gerador.gerar(f, raiz) for f in gerador.CATALOGO}


def _junto(s: str) -> str:
    return " ".join(s.split())


def _resultado(pasta: Path, tmp_path: Path, fake: FakeCliente):
    return Extrator(cliente=fake, cache=Cache(tmp_path / "cache", ativo=False)).processar(pasta)


def test_catalogo_cobre_os_tres_eixos_da_demonstracao():
    assert {f.numero for f in gerador.CATALOGO} == set(ESPERADOS)
    assert [f for f in gerador.CATALOGO if "peticao" in f.injecao]
    assert [f for f in gerador.CATALOGO if set(f.injecao) & set(gerador.SUBSIDIOS)]
    assert [f for f in gerador.CATALOGO if not f.injecao]


@pytest.mark.parametrize("ficha", gerador.CATALOGO, ids=lambda f: f.numero)
def test_nomes_dos_arquivos_dao_as_flags_de_subsidio(ficha: gerador.Ficha, catalogo: dict[str, Path]):
    pasta = catalogo[ficha.numero]
    subs = subsidios_por_arquivos(a.name for a in (pasta / "subsidios").iterdir())
    assert sorted(subs.presentes()) == sorted(ficha.subsidios)
    assert len(list((pasta / "autos").iterdir())) == 1


@pytest.mark.parametrize("ficha", gerador.CATALOGO, ids=lambda f: f.numero)
def test_peticao_gerada_entrega_os_fatos_que_a_regra_usa(ficha: gerador.Ficha, catalogo: dict[str, Path],
                                                         tmp_path: Path, fake: FakeCliente):
    dados = _resultado(catalogo[ficha.numero], tmp_path, fake).dados
    assert dados.numero == ficha.numero
    assert dados.uf == ficha.uf
    assert dados.valor_causa == ficha.valor_causa
    assert dados.autor.nome and dados.autor.nome.upper() == ficha.autor
    assert dados.advogado_autor.oab == f"{ficha.uf} {ficha.oab}"
    assert dados.comarca == ficha.cidade
    assert dados.contrato.valor == ficha.valor_contrato
    assert dados.contrato.parcelas == ficha.parcelas


@pytest.mark.parametrize("ficha", gerador.CATALOGO, ids=lambda f: f.numero)
def test_sinais_por_regra_saem_como_a_ficha_pediu(ficha: gerador.Ficha, catalogo: dict[str, Path],
                                                  tmp_path: Path, fake: FakeCliente):
    obrigatorios, proibidos = ESPERADOS[ficha.numero]
    codigos = {s.codigo for s in _resultado(catalogo[ficha.numero], tmp_path, fake).dados.sinais_alerta}
    assert obrigatorios <= codigos
    assert not (proibidos & codigos)


def test_injecao_no_subsidio_do_banco_sai_do_brief_e_marca_o_arquivo(catalogo: dict[str, Path], tmp_path: Path,
                                                                     fake: FakeCliente):
    ficha = next(f for f in gerador.CATALOGO if "laudo_referenciado" in f.injecao)
    pasta = catalogo[ficha.numero]
    res = _resultado(pasta, tmp_path, fake)
    arquivo = gerador.SUBSIDIOS["laudo_referenciado"][0] + ".pdf"
    bruto = _junto(texto.ler(pasta / "subsidios" / arquivo, pasta).texto)
    for oculto in gerador.INJECOES_BANCO:
        trecho = _junto(oculto.linhas[0])[:40]
        assert trecho in bruto, trecho  # o texto está mesmo escondido no PDF
        assert trecho not in _junto(res.brief), trecho  # e não chega ao modelo
        assert trecho not in _junto(fake.chamadas[0]), trecho
    suspeitos = [s for s in res.dados.sinais_alerta if s.codigo == "DOCUMENTO_SUSPEITO"]
    assert [s.fonte for s in suspeitos] == [arquivo]
    assert all(s.severidade == "alta" for s in suspeitos)
