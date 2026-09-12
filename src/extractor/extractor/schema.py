"""Esquema da resposta do LLM (structured outputs em modo estrito).

Tipos simples, todos os campos obrigatórios e anuláveis quando cabe, sem defaults nem validações
numéricas: o esquema JSON precisa ser aceito pela API. O mapeamento para os contratos de
`core.docs` (DadosExtraidos, Analise) fica em `pipeline.py`; os campos extras que o contrato ainda
não tem (dano moral, parcelas pagas, saldo devedor, liveness, contradições) ficam guardados no cache.
"""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict

Canal = Literal["app", "internet_banking", "agencia", "correspondente", "telefone", "desconhecido"]
Assinatura = Literal["fisica", "digital", "biometria", "ausente", "desconhecida"]
Liveness = Literal["confirmado", "nao_localizado", "nao_aplicavel", "desconhecido"]
Severidade = Literal["baixa", "media", "alta"]
CodigoSinal = Literal[
    "IDOSO", "CREDITO_CONTA_TERCEIRO", "BOLETIM_OCORRENCIA", "RECLAMACAO_BACEN", "SEM_CONTRATO",
    "ASSINATURA_DIVERGENTE", "CANAL_DIGITAL_SEM_PERFIL", "LIVENESS_AUSENTE_CANAL_DIGITAL", "OUTRO",
]


class _Estrito(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PessoaLLM(_Estrito):
    nome: str | None
    idade: int | None
    cpf_mascarado: str | None
    email: str | None
    telefone: str | None


class AdvogadoLLM(PessoaLLM):
    oab: str | None


class ContratoLLM(_Estrito):
    numero: str | None
    canal: Canal
    canal_alegado_pelo_autor: str | None
    assinatura: Assinatura
    liveness: Liveness
    credito_conta_terceiro: bool | None
    banco_deposito: str | None
    valor: float | None
    parcelas: int | None
    valor_parcela: float | None
    parcelas_pagas: int | None
    saldo_devedor: float | None
    data: str | None  # AAAA-MM-DD


class SinalLLM(_Estrito):
    codigo: CodigoSinal
    descricao: str
    severidade: Severidade
    fonte: str | None


class DadosLLM(_Estrito):
    comarca: str | None
    uf: str | None
    valor_causa: float | None
    dano_moral_pedido: float | None
    pedidos: list[str]
    autor: PessoaLLM
    advogado_autor: AdvogadoLLM
    contrato: ContratoLLM
    sinais_alerta: list[SinalLLM]
    resumo_fatos: str
    confianca: float


class AnaliseLLM(_Estrito):
    tese_provavel_autor: str
    pontos_fortes_banco: list[str]
    pontos_fracos_banco: list[str]
    contradicoes: list[str]
    riscos: list[str]
    texto: str


class SaidaLLM(_Estrito):
    dados: DadosLLM
    analise: AnaliseLLM


def hash_esquema(modelo: type[BaseModel] = SaidaLLM) -> str:
    """Muda quando o esquema muda; entra na chave do cache."""
    bruto = json.dumps(modelo.model_json_schema(), sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(bruto.encode("utf-8")).hexdigest()[:16]
