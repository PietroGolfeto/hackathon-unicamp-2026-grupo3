"""Constantes do projeto. Nenhum outro módulo deve repetir nomes de coluna, rótulos ou caminhos."""

from __future__ import annotations

import os
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
DIR_DATA = RAIZ / "data"
DIR_RAW = DIR_DATA / "raw"
DIR_CACHE = DIR_DATA / "cache"
DIR_EXEMPLOS = DIR_DATA / "exemplos"
DIR_MODELS = RAIZ / "models"
DIR_DOCS = RAIZ / "docs"
DIR_BACKTEST = DIR_DOCS / "backtest"

ARQ_RAW_XLSX = Path(os.environ.get("ENTEROS_RAW_XLSX", DIR_RAW / "Hackaton_Enter_Base_Candidatos.xlsx"))
ARQ_SINTETICOS = DIR_EXEMPLOS / "sinteticos.csv"
ARQ_CACHE_PARQUET = DIR_CACHE / "base.parquet"
ARQ_POLITICA = Path(__file__).resolve().parent / "policy" / "policy.yaml"
ARQ_MODELO_PERDA = DIR_MODELS / "modelo_perda.json"
ARQ_SEGMENTOS = DIR_MODELS / "segmentos.json"
ARQ_RATIO = DIR_MODELS / "ratio_condenacao.json"
ARQ_RESUMO_BACKTEST = DIR_BACKTEST / "resumo.json"

# Abas da planilha original
ABA_RESULTADOS = "Resultados dos processos"
ABA_SUBSIDIOS = "Subsídios disponibilizados"

# Colunas originais → canônicas (snake_case, sem acento)
COLUNAS_RESULTADOS = {
    "Número do processo": "numero",
    "UF": "uf",
    "Assunto": "assunto",
    "Sub-assunto": "sub_assunto",
    "Resultado macro": "resultado_macro",
    "Resultado micro": "resultado_micro",
    "Valor da causa": "valor_causa",
    "Valor da condenação/indenização": "valor_condenacao",
}
COLUNAS_SUBSIDIOS = {
    "Número do processos": "numero",  # sic: a aba de subsídios tem "processos"
    "Número do processo": "numero",
    "Contrato": "contrato",
    "Extrato": "extrato",
    "Comprovante de crédito": "comprovante",
    "Dossiê": "dossie",
    "Demonstrativo de evolução da dívida": "demonstrativo",
    "Laudo referenciado": "laudo",
}

# Subsídios: os 6 flags e o subconjunto com poder preditivo (dossiê e laudo não movem o resultado na base)
DOCS = ("contrato", "extrato", "comprovante", "dossie", "demonstrativo", "laudo")
DOCS_PREDITIVOS = ("contrato", "extrato", "comprovante", "demonstrativo")
DOCS_CRITICOS = ("contrato", "extrato")
NOME_DOC = {
    "contrato": "Contrato",
    "extrato": "Extrato",
    "comprovante": "Comprovante de crédito (BACEN)",
    "dossie": "Dossiê",
    "demonstrativo": "Demonstrativo de evolução da dívida",
    "laudo": "Laudo referenciado",
}

# Rótulos
EXITO = "Êxito"
NAO_EXITO = "Não Êxito"
SUB_GOLPE = "Golpe"
SUB_GENERICO = "Genérico"
SUB_ASSUNTOS = (SUB_GOLPE, SUB_GENERICO)
MICRO_ACORDO = "Acordo"
MICRO_EXTINCAO = "Extinção"
MICRO_IMPROCEDENCIA = "Improcedência"
MICRO_PARCIAL = "Parcial procedência"
MICRO_PROCEDENCIA = "Procedência"

# Decisões e faixas da política
DECISAO_DEFESA = "defesa"
DECISAO_ACORDO = "acordo"
DECISAO_INSTRUIR = "instruir"  # solicitar subsídio antes de decidir; se não vier, vira acordo
FAIXA_VERDE = "verde"
FAIXA_AMARELA = "amarela"
FAIXA_VERMELHA = "vermelha"

STATUS_PRESENTE = "presente"
STATUS_AUSENTE = "ausente"
STATUS_INCONSISTENTE = "inconsistente"

# Justiça Estadual: código do tribunal no número CNJ → UF
TJ_UF = {
    "01": "AC", "02": "AL", "03": "AP", "04": "AM", "05": "BA", "06": "CE", "07": "DF", "08": "ES", "09": "GO",
    "10": "MA", "11": "MT", "12": "MS", "13": "MG", "14": "PA", "15": "PB", "16": "PR", "17": "PE", "18": "PI",
    "19": "RJ", "20": "RN", "21": "RS", "22": "RO", "23": "RR", "24": "SC", "25": "SE", "26": "SP", "27": "TO",
}
UFS = tuple(sorted(TJ_UF.values()))

SEMENTE = 42
