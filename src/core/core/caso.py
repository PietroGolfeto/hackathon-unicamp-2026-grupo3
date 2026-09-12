"""Entrada comum a modelo, extrator e política: o caso reduzido às features que a base tem."""

from __future__ import annotations

from pydantic import BaseModel, Field

NOMES_SUBSIDIOS: dict[str, str] = {
    "contrato": "Contrato",
    "extrato": "Extrato",
    "comprovante_credito": "Comprovante de crédito",
    "dossie": "Dossiê",
    "demonstrativo_divida": "Demonstrativo de evolução da dívida",
    "laudo_referenciado": "Laudo referenciado",
}


# Códigos previstos de sinal de alerta extraídos dos autos (P3). A política referencia
# estes códigos em sinais_forcam_acordo; a UI usa a descrição.
CODIGOS_SINAIS: dict[str, str] = {
    "IDOSO": "Autor idoso",
    "CREDITO_CONTA_TERCEIRO": "Crédito caiu em conta de terceiro",
    "BOLETIM_OCORRENCIA": "Há boletim de ocorrência",
    "RECLAMACAO_BACEN": "Há reclamação no BACEN",
    "SEM_CONTRATO": "Banco não apresentou o contrato",
    "ASSINATURA_DIVERGENTE": "Assinatura divergente dos documentos",
    "CANAL_DIGITAL_SEM_PERFIL": "Contratação digital sem perfil compatível do autor",
}


class Subsidios(BaseModel):
    """As seis flags do CSV de subsídios; True = o banco forneceu o documento."""

    contrato: bool = False
    extrato: bool = False
    comprovante_credito: bool = False
    dossie: bool = False
    demonstrativo_divida: bool = False
    laudo_referenciado: bool = False

    def presentes(self) -> list[str]:
        return [k for k in NOMES_SUBSIDIOS if getattr(self, k)]

    def ausentes(self) -> list[str]:
        return [k for k in NOMES_SUBSIDIOS if not getattr(self, k)]

    @property
    def n(self) -> int:
        return len(self.presentes())


class CasoFeatures(BaseModel):
    numero: str
    uf: str
    sub_assunto: str | None = None
    valor_causa: float = Field(ge=0)
    subsidios: Subsidios = Field(default_factory=Subsidios)
    sinais: dict[str, object] = Field(default_factory=dict)  # extras de P3 (codigo -> valor)
