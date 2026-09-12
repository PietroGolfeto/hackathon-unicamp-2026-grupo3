"""Leitura tipada do policy.yaml."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import BaseModel

from enteros import config as cfg


class Faixas(BaseModel):
    limiar_verde: float
    limiar_vermelha: float
    voi_min_pct_causa: float
    prazo_instrucao_dias: int


class Custos(BaseModel):
    custo_escritorio_defesa: float
    custo_escritorio_acordo: float
    honorarios_sucumbencia_pct: float
    custas_pct_valor_causa: float
    taxa_correcao_mensal: float
    prazo_medio_meses: int
    custo_recuperar_subsidio: float

    @property
    def fator_tempo(self) -> float:
        return (1 + self.taxa_correcao_mensal) ** self.prazo_medio_meses


class Oferta(BaseModel):
    aceite_s50: float
    aceite_largura: float
    margem_teto: float
    piso_pct_causa: float
    teto_pct_causa: float
    desconto_abertura: float
    arredondamento: float
    grade_passo: float


class RegrasDuras(BaseModel):
    sinais_forcam_acordo: list[str]
    inconsistente_vale_ausente: bool


class Experimento(BaseModel):
    fracao_exploracao: float
    bandas_pct_causa: list[float]


class Politica(BaseModel):
    versao: str
    faixas: Faixas
    custos: Custos
    oferta: Oferta
    regras_duras: RegrasDuras
    experimento: Experimento


@lru_cache(maxsize=4)
def carregar_politica(caminho: Path | None = None) -> Politica:
    caminho = Path(caminho) if caminho else cfg.ARQ_POLITICA
    with open(caminho, encoding="utf-8") as f:
        return Politica.model_validate(yaml.safe_load(f))
