from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from conftest import pdf_de_texto
from core.caso import Subsidios

from extractor import __main__ as cli
from extractor.caso import (
    ExtracaoCaso,
    ler_caso,
    para_case_features,
    resumir_caso,
)
from extractor.leitura import ErroLeitura
from extractor.resumo import ErroResumo

SUBSIDIOS_MARIA = [
    "02_Contrato_502348719.pdf", "03_Extrato_Bancario.pdf", "04_Comprovante_de_Credito_BACEN.pdf",
    "05_Dossie_Veritas.pdf", "06_Demonstrativo_Evolucao_Divida.pdf", "07_Laudo_Referenciado.pdf",
]
SUBSIDIOS_JOSE = [
    "02_Comprovante_de_Credito_BACEN.pdf", "03_Demonstrativo_Evolucao_Divida.pdf",
    "04_Laudo_Referenciado.pdf",
]


def _extracao(**campos: Any) -> ExtracaoCaso:
    base: dict[str, Any] = {
        "numero_processo": "0801234-56-2024-8-10-0001", "comarca": "São Luís/MA", "uf": "MA",
        "autor_nome": "Maria das Graças Silva Pereira", "autor_idade": 72, "valor_causa": 20000.0,
        "dano_moral_pedido": 15000.0, "contrato_valor": 5000.0, "contrato_parcelas": 84, "valor_parcela": 120.0,
        "parcelas_pagas": None, "saldo_devedor": None,
        "canal_contratacao": "Correspondente bancário por telemarketing", "assinatura": "Manuscrita",
        "sub_assunto": "Genérico", "destaques_subsidios": ["Dossiê: assinatura 91%, liveness 97,3%"],
        "prova_de_proveito": ["crédito de R$ 5.000 na conta da autora", "TED para conta própria Bradesco"],
        "conta_credito_titular_autor": True, "liveness_presente": True, "indicios": ["boletim de ocorrência"],
        "contradicoes": ['Petição (p. 3): "inexistindo nos extratos movimentação" × Extrato (p. 1): TED, PIX e saque'],
    }
    return ExtracaoCaso(**{**base, **campos})


EXTRACAO_JOSE = _extracao(
    numero_processo="0654321-09.2024.8.04.0001", comarca="Manaus", uf="AM",
    autor_nome="José Raimundo Oliveira Costa", autor_idade=61, valor_causa=25000.0,
    dano_moral_pedido=18000.0, canal_contratacao="App mobile self-service",
    assinatura="Biometria facial", sub_assunto="Golpe", conta_credito_titular_autor=False,
    liveness_presente=False, indicios=["Autor é idoso (61 anos)", "boletim de ocorrência", "reclamação BACEN"], contradicoes=[],
    prova_de_proveito=["crédito em conta Caixa que o autor diz não ter"],
    destaques_subsidios=["Laudo: vídeo de liveness não localizado", "Dossiê: biometria facial + senha"],
)


class ClienteFalso:
    def __init__(self, saida: ExtracaoCaso) -> None:
        self.chamadas: list[dict[str, Any]] = []
        self.responses = SimpleNamespace(parse=self._parse)
        self._saida = saida

    def _parse(self, **kwargs: Any) -> SimpleNamespace:
        self.chamadas.append(kwargs)
        return SimpleNamespace(output_parsed=self._saida)


def _pasta_do_caso(raiz: Path, autos: str, subsidios: list[str]) -> Path:
    raiz.mkdir()
    (raiz / autos).write_bytes(pdf_de_texto([["PETICAO INICIAL", "Nunca usou os valores."]]))
    for nome in subsidios:
        (raiz / nome).write_bytes(pdf_de_texto([[Path(nome).stem.upper()]]))
    return raiz


def test_ler_caso_poe_autos_primeiro_e_classifica_subsidios(tmp_path: Path) -> None:
    pasta = _pasta_do_caso(tmp_path / "processo_01", "01_Autos_Processo_0801234.pdf", SUBSIDIOS_MARIA)

    docs = ler_caso(pasta)

    assert [d.tipo for d in docs] == ["autos"] + ["subsidio"] * 6
    assert docs[0].nome == "01_Autos_Processo_0801234.pdf"
    assert "[página 1]\nPETICAO INICIAL" in docs[0].texto


def test_ler_caso_aceita_layout_autos_e_subsidios_do_ingest(tmp_path: Path) -> None:
    pasta = tmp_path / "0654321-09.2024.8.04.0001"
    (pasta / "autos").mkdir(parents=True)
    (pasta / "subsidios").mkdir()
    (pasta / "autos" / "documento.pdf").write_bytes(pdf_de_texto([["PETICAO"]]))
    (pasta / "subsidios" / "laudo.pdf").write_bytes(pdf_de_texto([["LAUDO"]]))

    assert [(d.nome, d.tipo) for d in ler_caso(pasta)] == [
        ("documento.pdf", "autos"), ("laudo.pdf", "subsidio"),
    ]


def test_ler_caso_sem_peticao_e_erro(tmp_path: Path) -> None:
    pasta = tmp_path / "so_subsidios"
    pasta.mkdir()
    (pasta / "03_Extrato_Bancario.pdf").write_bytes(pdf_de_texto([["EXTRATO"]]))

    with pytest.raises(ErroLeitura, match="nenhuma petição"):
        ler_caso(pasta)


def test_para_case_features_mapeia_subsidios_e_sinais_da_extracao() -> None:
    subsidios = Subsidios(comprovante_credito=True, demonstrativo_divida=True, laudo_referenciado=True)

    caso = para_case_features(EXTRACAO_JOSE, subsidios)

    assert caso.docs.comprovante == "presente" and caso.docs.laudo == "presente"
    assert caso.docs.contrato == "ausente" and caso.docs.extrato == "ausente"
    assert caso.conta_deposito_titular_autor is False and caso.liveness_presente is False
    assert (caso.uf, caso.sub_assunto, caso.valor_causa) == ("AM", "Golpe", 25000.0)


def test_uf_vem_do_numero_cnj_quando_a_extracao_nao_traz() -> None:
    caso = para_case_features(_extracao(uf=None), Subsidios())

    assert caso.uf == "MA"
    assert caso.numero == "0801234-56.2024.8.10.0001"


def test_sem_valor_da_causa_nao_chama_o_engine() -> None:
    with pytest.raises(ErroResumo, match="valor da causa"):
        para_case_features(_extracao(valor_causa=None), Subsidios())


def test_ficha_maria_defender_com_contradicao(tmp_path: Path) -> None:
    pasta = _pasta_do_caso(tmp_path / "processo_01", "01_Autos_Processo_0801234.pdf", SUBSIDIOS_MARIA)
    cliente = ClienteFalso(_extracao())

    ficha = resumir_caso(pasta, client=cliente, modelo="gpt-teste")
    texto = ficha.texto()

    entrada = cliente.chamadas[0]["input"]
    assert entrada.startswith("=== 01_Autos_Processo_0801234.pdf (autos) ===")
    assert "=== 07_Laudo_Referenciado.pdf (subsídio) ===" in entrada
    assert cliente.chamadas[0]["text_format"] is ExtracaoCaso
    assert texto.startswith("CASO 0801234-56.2024.8.10.0001 - MARIA DAS GRAÇAS SILVA PEREIRA (SÃO LUÍS/MA)")
    assert "Canal: Correspondente bancário por telemarketing, assinatura manuscrita" in texto
    assert "Subsídios: 6/6 (contrato, extrato, comprovante BACEN, dossiê, demonstrativo, laudo)" in texto
    assert "Segmento na base: MA, Genérico, 4/4 docs-chave" in texto
    assert "Decisão: DEFENDER" in texto
    assert texto.count("inexistindo nos extratos movimentação") == 1  # não repete nos motivos
    assert ficha.recomendacao.decisao == "defesa"


def test_ficha_jose_acordo_com_escada(tmp_path: Path) -> None:
    pasta = _pasta_do_caso(tmp_path / "processo_02", "01_Autos_Processo_0654321.pdf", SUBSIDIOS_JOSE)

    ficha = resumir_caso(pasta, client=ClienteFalso(EXTRACAO_JOSE), modelo="gpt-teste")
    texto = ficha.texto()

    assert ficha.recomendacao.decisao == "acordo"
    assert "Subsídios: 3/6 (comprovante BACEN, demonstrativo, laudo) - sem contrato, sem extrato, sem dossiê" in texto
    assert "AM, Golpe, 2/4 docs-chave (comprovante BACEN + demonstrativo)" in texto
    assert "idoso(a), 61 anos, boletim de ocorrência, reclamação BACEN, pede R$ 18.000 de dano moral, VC R$ 25.000" in texto
    assert "Decisão: ACORDO: abrir em R$ " in texto and "% do VC), alvo R$ " in texto
    assert "cancelar contrato" in texto
    assert "Destaques: Laudo: vídeo de liveness não localizado\n" in texto
    assert "Dossiê:" not in texto  # não há dossiê na pasta do José


def test_cli_com_pasta_imprime_a_ficha(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    pasta = _pasta_do_caso(tmp_path / "processo_02", "01_Autos_Processo_0654321.pdf", SUBSIDIOS_JOSE)
    ficha = resumir_caso(pasta, client=ClienteFalso(EXTRACAO_JOSE), modelo="gpt-teste")
    monkeypatch.setattr(cli, "resumir_caso", lambda caminho, modelo=None: ficha)

    assert cli.main([str(pasta)]) == 0
    assert capsys.readouterr().out.startswith("CASO 0654321-09.2024.8.04.0001 - JOSÉ")
