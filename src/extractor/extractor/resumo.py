"""Resumo dos principais pontos de um PDF: texto pelo pdf-inspector, síntese pela OpenAI."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from openai import OpenAI
from pydantic import BaseModel, Field

from extractor.leitura import TextoPdf, ler_pdf

MODELO_PADRAO = "gpt-4o-mini"
# ~50 mil tokens: cabe com folga no contexto do modelo padrão; o excedente é cortado e sinalizado.
LIMITE_CARACTERES = 200_000

INSTRUCOES = """\
Você é assistente jurídico de um banco que responde a processos de empréstimo não reconhecido.
Resuma o documento para um advogado que tem poucos minutos para lê-lo.

Regras:
- Use só o que está no texto. Não invente fatos, valores, datas ou nomes.
- Se uma informação não consta, não a mencione.
- pontos_principais: de 5 a 10 itens curtos, cada um com um fato concreto do documento
  (partes, pedidos, valores, datas, contratos, provas, alegações, prazos).
  Quando o texto marcar a página, termine o item com "(p. N)".
- resumo: um parágrafo de até 120 palavras dizendo o que é o documento e o que ele sustenta.
- Escreva em português.
"""


class ErroResumo(Exception):
    """Falha ao gerar o resumo, com mensagem legível pelo usuário."""


class _SaidaLLM(BaseModel):
    resumo: str
    pontos_principais: list[str]


class ResumoDocumento(BaseModel):
    arquivo: str
    paginas: int
    tipo_pdf: str
    paginas_ocr: list[int] = Field(default_factory=list)
    paginas_sem_texto: list[int] = Field(default_factory=list)
    texto_truncado: bool = False
    modelo: str
    resumo: str
    pontos_principais: list[str]
    gerado_em: datetime


def _cliente() -> OpenAI:
    if not os.environ.get("OPENAI_API_KEY"):
        raise ErroResumo("defina OPENAI_API_KEY no .env para gerar o resumo")
    return OpenAI()


def resumir_texto(texto: str, client: Any = None, modelo: str | None = None) -> _SaidaLLM:
    """Pede à OpenAI resumo e pontos principais em saída estruturada."""
    if not texto.strip():
        raise ErroResumo("o documento não tem texto para resumir")
    client = client or _cliente()
    resposta = client.responses.parse(
        model=modelo or os.environ.get("OPENAI_MODEL") or MODELO_PADRAO,
        instructions=INSTRUCOES,
        input=texto[:LIMITE_CARACTERES],
        text_format=_SaidaLLM,
    )
    if resposta.output_parsed is None:
        raise ErroResumo("o modelo não devolveu um resumo; tente de novo")
    return resposta.output_parsed


def resumir_pdf(caminho: Path | str, client: Any = None, modelo: str | None = None) -> ResumoDocumento:
    """Lê o PDF (com OCR nas páginas que precisarem) e resume os principais pontos."""
    texto: TextoPdf = ler_pdf(caminho)
    modelo = modelo or os.environ.get("OPENAI_MODEL") or MODELO_PADRAO
    saida = resumir_texto(texto.markdown, client=client, modelo=modelo)
    return ResumoDocumento(
        arquivo=Path(caminho).name,
        paginas=texto.paginas,
        tipo_pdf=texto.tipo_pdf,
        paginas_ocr=texto.paginas_ocr,
        paginas_sem_texto=texto.paginas_sem_texto,
        texto_truncado=len(texto.markdown) > LIMITE_CARACTERES,
        modelo=modelo,
        resumo=saida.resumo,
        pontos_principais=saida.pontos_principais,
        gerado_em=datetime.now(UTC),
    )
