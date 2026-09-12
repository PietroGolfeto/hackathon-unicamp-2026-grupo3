"""Contrato de P3: o que sai dos PDFs (dados, sinais), a análise jurídica e as minutas."""

from __future__ import annotations

import re
from collections.abc import Iterable
from datetime import date, datetime
from pathlib import Path
from typing import Literal, Protocol

from pydantic import BaseModel, Field

from core.caso import CasoFeatures, Subsidios
from core.modelo import Scores
from core.politica import Recomendacao

Severidade = Literal["baixa", "media", "alta"]


class Pessoa(BaseModel):
    nome: str | None = None
    cpf_mascarado: str | None = None
    idade: int | None = None
    email: str | None = None
    telefone: str | None = None


class Advogado(Pessoa):
    oab: str | None = None


class ContratoInfo(BaseModel):
    canal: Literal[
        "app", "internet_banking", "agencia", "correspondente", "telefone", "desconhecido"
    ] = "desconhecido"
    assinatura: Literal["fisica", "digital", "biometria", "ausente", "desconhecida"] = "desconhecida"
    credito_conta_terceiro: bool | None = None
    valor: float | None = None
    parcelas: int | None = None
    data: date | None = None


class SinalAlerta(BaseModel):
    codigo: str
    descricao: str
    severidade: Severidade
    fonte: str | None = None  # arquivo ou trecho de onde saiu


class DadosExtraidos(BaseModel):
    numero: str
    origem: Literal["llm", "stub"]
    modelo: str | None = None
    autor: Pessoa = Field(default_factory=Pessoa)
    advogado_autor: Advogado = Field(default_factory=Advogado)
    comarca: str | None = None
    uf: str | None = None
    valor_causa: float | None = None
    pedidos: list[str] = Field(default_factory=list)
    contrato: ContratoInfo = Field(default_factory=ContratoInfo)
    sinais_alerta: list[SinalAlerta] = Field(default_factory=list)
    resumo_fatos: str = ""
    confianca: float = Field(default=0.0, ge=0, le=1)
    gerado_em: datetime

    def codigos_sinais(self) -> list[str]:
        return [s.codigo for s in self.sinais_alerta]


class Analise(BaseModel):
    """Independe da decisão; nunca fica obsoleta quando a política muda."""

    numero: str
    origem: str
    pontos_fortes_banco: list[str] = Field(default_factory=list)
    pontos_fracos_banco: list[str] = Field(default_factory=list)
    tese_provavel_autor: str = ""
    riscos: list[str] = Field(default_factory=list)
    texto: str = ""


class Minutas(BaseModel):
    """Depende da recomendação; guarda a política sob a qual foi redigida."""

    numero: str
    politica_id: int | None = None
    origem: str
    proposta_acordo: str = ""
    roteiro_defesa: str = ""
    mensagem_contato: str = ""


class ExtratorDocs(Protocol):
    def extrair(self, processo_dir: Path, numero: str) -> DadosExtraidos: ...

    def analisar(self, caso: CasoFeatures, dados: DadosExtraidos, scores: Scores) -> Analise: ...

    def redigir(self, caso: CasoFeatures, dados: DadosExtraidos, rec: Recomendacao) -> Minutas: ...


# Nome de arquivo -> flag de subsídio. Serve ao ingest e ao extrator stub.
_PADROES_SUBSIDIO: tuple[tuple[str, str], ...] = (
    ("contrato", r"contrat"),
    ("extrato", r"extrato"),
    ("comprovante_credito", r"comprovante|cr[eé]dito"),
    ("dossie", r"dossi"),
    ("demonstrativo_divida", r"demonstrativo|evolu"),
    ("laudo_referenciado", r"laudo"),
)


def subsidios_por_arquivos(nomes: Iterable[str]) -> Subsidios:
    """Deduz as seis flags pelos nomes dos arquivos da pasta subsidios/ de um processo."""
    flags = {chave: False for chave, _ in _PADROES_SUBSIDIO}
    for nome in nomes:
        base = Path(str(nome)).stem.lower()
        for chave, padrao in _PADROES_SUBSIDIO:
            if re.search(padrao, base):
                flags[chave] = True
    return Subsidios(**flags)
