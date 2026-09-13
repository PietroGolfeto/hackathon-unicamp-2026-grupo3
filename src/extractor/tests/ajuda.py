"""Ajuda dos testes (parte do LLM): saída completa do esquema e dublê do cliente."""

from __future__ import annotations

from ajuda_docs import NUMERO  # noqa: F401 - reexport para os testes
from pydantic import BaseModel

from extractor.llm import Resposta
from extractor.schema import (
    AdvogadoLLM,
    AnaliseLLM,
    ComentarioDocLLM,
    ContratoLLM,
    DadosLLM,
    PessoaLLM,
    SaidaLLM,
    SinalLLM,
)


def saida_exemplo() -> SaidaLLM:
    return SaidaLLM(
        dados=DadosLLM(
            comarca="Belo Horizonte", uf="MG", valor_causa=None, dano_moral_pedido=12000.0,
            pedidos=["inexistência do débito", "repetição em dobro", "danos morais R$ 12.000,00"],
            autor=PessoaLLM(nome="Ana Lúcia Ferreira Mota", idade=None, cpf_mascarado="321.654.987-00",
                            email=None, telefone=None),
            advogado_autor=AdvogadoLLM(nome="Paula Reis Andrade", idade=None, cpf_mascarado=None,
                                       email="paula.andrade@adv.com.br", telefone=None, oab="MG 45.678"),
            contrato=ContratoLLM(numero="700112233", canal="app", canal_alegado_pelo_autor="nega uso de app",
                                 assinatura="digital", liveness="nao_localizado", credito_conta_terceiro=True,
                                 banco_deposito="Caixa Econômica Federal", valor=4000.0, parcelas=60,
                                 valor_parcela=110.0, parcelas_pagas=3, saldo_devedor=3100.0, data="2023-03-03"),
            sinais_alerta=[
                SinalLLM(codigo="IDOSO", descricao="Autora com 69 anos", severidade="media", fonte="peticao_inicial.txt"),
                SinalLLM(codigo="CREDITO_CONTA_TERCEIRO", descricao="Crédito em conta da Caixa que a autora nega ter",
                         severidade="alta", fonte="comprovante_credito.txt"),
            ],
            comentarios_documentos=[
                ComentarioDocLLM(arquivo="peticao_inicial.txt", relevancia="alta",
                                 comentario="Autora nega a contratação por app e pede a inexistência do débito."),
                ComentarioDocLLM(arquivo="comprovante_credito.txt", relevancia="alta",
                                 comentario="Mostra crédito de 4000,00 em conta da Caixa que a autora nega ter."),
                ComentarioDocLLM(arquivo="nao_existe.txt", relevancia="baixa",
                                 comentario="Arquivo que não está no brief; deve ser descartado no mapeamento."),
            ],
            resumo_fatos="Autora idosa nega contratação por app; crédito caiu em conta da Caixa que ela diz não ter.",
            confianca=0.6,
        ),
        analise=AnaliseLLM(
            tese_provavel_autor="Fraude por terceiro em canal digital; responsabilidade objetiva (Súmula 479).",
            pontos_fortes_banco=["[Laudo] Autenticação por biometria e senha registrada"],
            pontos_fracos_banco=["[Laudo] Vídeo de liveness não localizado", "Contrato e extrato não apresentados"],
            contradicoes=["Petição afirma que a autora não possui conta na Caixa; [Comprovante] indica depósito na Caixa"],
            riscos=["Idosa sem perfil digital", "Boletim de ocorrência e reclamação no BACEN"],
            texto="Parecer: prova do banco frágil sem contrato, extrato e liveness.",
        ),
    )


class FakeCliente:
    """Devolve sempre a mesma saída e conta as chamadas."""

    modelo = "fake-1"

    def __init__(self, saida: SaidaLLM | None = None) -> None:
        self.saida = saida or saida_exemplo()
        self.chamadas: list[str] = []

    def completar[T: BaseModel](self, instrucoes: str, entrada: str, esquema: type[T]) -> Resposta[T]:
        self.chamadas.append(entrada)
        assert esquema is SaidaLLM
        return Resposta(saida=self.saida, modelo=self.modelo, tokens_entrada=1000, tokens_saida=200)  # type: ignore[arg-type]
