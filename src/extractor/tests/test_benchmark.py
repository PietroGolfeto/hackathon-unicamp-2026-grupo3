from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from conftest import pdf_de_texto
from core.caso import Subsidios

from extractor import benchmark
from extractor.benchmark import GABARITOS, avaliar, custo
from extractor.caso import ExtracaoCaso

SUBSIDIOS_MARIA = Subsidios(
    contrato=True, extrato=True, comprovante_credito=True, dossie=True,
    demonstrativo_divida=True, laudo_referenciado=True,
)
SUBSIDIOS_JOSE = Subsidios(comprovante_credito=True, demonstrativo_divida=True, laudo_referenciado=True)


def _perfeita(caso: str, **campos: Any) -> ExtracaoCaso:
    """Extração que acerta tudo do gabarito; `campos` estraga o que o teste quiser."""
    comum: dict[str, Any] = {"numero_processo": None, "autor_nome": None, "saldo_devedor": None}
    por_caso: dict[str, dict[str, Any]] = {
        "processo_01": {
            "comarca": "São Luís", "uf": "MA", "autor_idade": 65, "valor_causa": 20000.0,
            "dano_moral_pedido": 15000.0, "contrato_valor": 5000.0, "contrato_parcelas": 72,
            "valor_parcela": 120.0, "parcelas_pagas": 21,
            "canal_contratacao": "Correspondente bancário por telemarketing", "assinatura": "manuscrita",
            "sub_assunto": "Genérico", "destaques_subsidios": ["Dossiê: assinatura 91%, liveness 97,3%"],
            "prova_de_proveito": ["TED R$ 3.000 p/ conta própria", "PIX R$ 1.500", "saque ATM R$ 485"],
            "conta_credito_titular_autor": True, "liveness_presente": True, "indicios": [],
            "contradicoes": ['Petição (p. 2): "inexistindo movimentação" × Extrato (p. 1): TED, PIX e saque'],
        },
        "processo_02": {
            "comarca": "Manaus", "uf": "AM", "autor_idade": 61, "valor_causa": 25000.0,
            "dano_moral_pedido": 18000.0, "contrato_valor": 8500.0, "contrato_parcelas": 84,
            "valor_parcela": 180.0, "parcelas_pagas": 8,
            "canal_contratacao": "App mobile self-service", "assinatura": "biometria facial",
            "sub_assunto": "Golpe", "destaques_subsidios": ["Laudo: vídeo de liveness não localizado"],
            "prova_de_proveito": ["crédito em conta Caixa que o autor diz não ter"],
            "conta_credito_titular_autor": False, "liveness_presente": False,
            "indicios": ["BO nº 2024.005432", "RDR BACEN nº 12345678-9"], "contradicoes": [],
        },
    }
    return ExtracaoCaso(**{**comum, **por_caso[caso], **campos})


def test_extracao_perfeita_passa_em_todos_os_criterios() -> None:
    checks = avaliar(_perfeita("processo_02"), SUBSIDIOS_JOSE, "acordo", GABARITOS["processo_02"])

    assert checks and all(checks.values()), [k for k, v in checks.items() if not v]


def test_criterios_pegam_alucinacao_contradicao_faltando_e_decisao_errada() -> None:
    jose = _perfeita(
        "processo_02",
        destaques_subsidios=["Dossiê: biometria facial"],
        contradicoes=['Petição (p. 1): "nunca assinou" × Contrato (p. 1): assinatura'],
        parcelas_pagas=None,
    )
    checks_jose = avaliar(jose, SUBSIDIOS_JOSE, "defesa", GABARITOS["processo_02"])
    checks_maria = avaliar(
        _perfeita("processo_01", contradicoes=[]), SUBSIDIOS_MARIA, "defesa", GABARITOS["processo_01"]
    )

    falhas_jose = {k for k, v in checks_jose.items() if not v}
    assert falhas_jose == {
        "sem_destaque_de_doc_ausente", "sem_contradicao_com_doc_ausente", "parcelas_pagas", "decisao",
    }
    assert {k for k, v in checks_maria.items() if not v} == {"contradicao_chave"}


def test_custo_desconta_cache_e_aceita_snapshot_datado() -> None:
    esperado = (8000 * 0.15 + 2000 * 0.075 + 1000 * 0.60) / 1_000_000

    assert custo("gpt-4o-mini-2024-07-18", entrada=10000, cache=2000, saida=1000) == pytest.approx(esperado)
    assert custo("modelo-sem-preco", 1, 0, 1) is None


class ClienteFalso:
    """Responde com a extração perfeita do caso pedido; o modelo "quebrado" levanta erro."""

    def __init__(self) -> None:
        self.responses = SimpleNamespace(parse=self._parse)

    def _parse(self, *, model: str, input: str, **_: Any) -> SimpleNamespace:
        if model == "quebrado":
            raise RuntimeError("modelo indisponível")
        caso = "processo_02" if "0654321" in input else "processo_01"
        uso = SimpleNamespace(
            input_tokens=9000, input_tokens_details=SimpleNamespace(cached_tokens=0),
            output_tokens=800, output_tokens_details=SimpleNamespace(reasoning_tokens=300),
        )
        return SimpleNamespace(output_parsed=_perfeita(caso), usage=uso)


def _pastas_exemplo(raiz: Path) -> Path:
    arquivos = {
        "processo_01": ["01_Autos_Processo_0801234.pdf", "02_Contrato.pdf", "03_Extrato_Bancario.pdf",
                        "04_Comprovante_de_Credito_BACEN.pdf", "05_Dossie_Veritas.pdf",
                        "06_Demonstrativo_Evolucao_Divida.pdf", "07_Laudo_Referenciado.pdf"],
        "processo_02": ["01_Autos_Processo_0654321.pdf", "02_Comprovante_de_Credito_BACEN.pdf",
                        "03_Demonstrativo_Evolucao_Divida.pdf", "04_Laudo_Referenciado.pdf"],
    }
    for caso, nomes in arquivos.items():
        (raiz / caso).mkdir(parents=True)
        for nome in nomes:
            (raiz / caso / nome).write_bytes(pdf_de_texto([[Path(nome).stem.upper()]]))
    return raiz


def test_benchmark_ponta_a_ponta_com_cliente_falso(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(benchmark, "_cliente", ClienteFalso)
    pasta = _pastas_exemplo(tmp_path / "exemplos")

    codigo = benchmark.main([
        "--modelos", "gpt-4o-mini", "quebrado", "--repeticoes", "2",
        "--pasta", str(pasta), "--saida", str(tmp_path / "saida"),
    ])

    assert codigo == 0
    tabela = capsys.readouterr().out
    linhas = [linha for linha in tabela.splitlines() if linha.startswith(("| gpt", "| queb"))]
    assert linhas[0].startswith("| gpt-4o-mini | 100% | 100% | 100% | 0 |")
    assert linhas[1].startswith("| quebrado | 0% |") and "4/4" in linhas[1]
    assert len(list((tmp_path / "saida").glob("benchmark_extractor_*.json"))) == 1
