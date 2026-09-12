from datetime import UTC, datetime

from core.caso import CasoFeatures, Subsidios
from core.docs import Analise, DadosExtraidos, Minutas, SinalAlerta, subsidios_por_arquivos
from core.modelo import Scores


def test_subsidios_contam_presentes_e_ausentes():
    s = Subsidios(contrato=True, extrato=True)
    assert s.n == 2
    assert s.presentes() == ["contrato", "extrato"]
    assert "comprovante_credito" in s.ausentes()


def test_subsidios_por_nome_de_arquivo():
    s = subsidios_por_arquivos([
        "Contrato_assinado.pdf", "extrato-conta.pdf", "Comprovante de Crédito.pdf",
        "dossie.pdf", "Demonstrativo_evolucao_divida.pdf", "documentos pessoais.pdf",
    ])
    assert s.contrato and s.extrato and s.comprovante_credito and s.dossie
    assert s.demonstrativo_divida and not s.laudo_referenciado
    assert subsidios_por_arquivos([]).n == 0


def test_dados_extraidos_com_defaults_e_sinais():
    d = DadosExtraidos(
        numero="0654321-09.2024.8.04.0001", origem="stub", gerado_em=datetime(2026, 9, 12, tzinfo=UTC),
        sinais_alerta=[SinalAlerta(codigo="IDOSO", descricao="72 anos", severidade="media")],
    )
    assert d.codigos_sinais() == ["IDOSO"]
    assert d.contrato.canal == "desconhecido"
    assert d.autor.nome is None


def test_caso_scores_analise_minutas_serializam():
    caso = CasoFeatures(numero="x", uf="MG", valor_causa=1000)
    s = Scores(numero="x", modelo_versao="v", origem="modelo", p_exito_defesa=0.5,
               condenacao_p20=1, condenacao_p50=2, condenacao_p80=3, gerado_em=datetime(2026, 1, 1, tzinfo=UTC))
    a = Analise(numero="x", origem="stub")
    m = Minutas(numero="x", origem="stub")
    for obj in (caso, s, a, m):
        assert type(obj).model_validate_json(obj.model_dump_json()) == obj
