"""Ajuda dos testes (parte do LLM): saída de exemplo no esquema e dublê do cliente."""

from __future__ import annotations

from ajuda_docs import NUMERO  # noqa: F401 - reexport para os testes
from pydantic import BaseModel

from extractor.llm import Resposta
from extractor.schema import SaidaLLM


def saida_exemplo() -> SaidaLLM:
    return SaidaLLM(
        resumo=[
            "[Petição] Ana Lúcia, 69 anos, nega ter contratado empréstimo de R$ 4.000,00 por aplicativo em 03/03/2023.",
            "[Comprovante] Crédito de R$ 4.000,00 em 04/03/2023 em conta da Caixa Econômica Federal, canal aplicativo mobile.",
            "[Demonstrativo] 3 de 60 parcelas de R$ 110,00 pagas; saldo devedor em aberto.",
            "[Laudo] Aceite eletrônico com biometria registrado; vídeo de liveness não localizado.",
            "[Petição] Boletim de ocorrência nº 2024.001122 e reclamação no BACEN (RDR 555555-1).",
        ],
        contradicoes=[
            'Petição afirma "não possui conta na Caixa"; [Comprovante] indica depósito na Caixa Econômica Federal.',
        ],
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
