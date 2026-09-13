"""Agregados de aderência e efetividade a partir de decisoes, recomendacoes e eventos."""

from __future__ import annotations

import json
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

import pandas as pd
from core.modelo import ModeloInfo
from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.models import (
    Decisao,
    Escritorio,
    Evento,
    ParecerJustificativa,
    Politica,
    Processo,
    Recomendacao,
    Usuario,
)
from app.services.recomendacao import params_de

ACEITES = ("aceito", "contraproposta_aceita")
COBERTURA_CONFIAVEL = 0.8
RESUMO_ENGINE = Path(__file__).resolve().parents[4] / "docs" / "backtest" / "resumo.json"


@lru_cache(maxsize=1)
def backtest_potencial() -> dict[str, Any] | None:
    """Carregue o resumo agregado e versionado do backtest do engine.

    Returns:
        Comparação financeira essencial, ou ``None`` quando o artefato não está disponível.
    """
    try:
        bruto = json.loads(RESUMO_ENGINE.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    return {
        "n_casos": bruto["n_casos"],
        "defender_tudo": bruto["custo_defender_tudo"],
        "acordar_tudo": bruto["custo_acordar_tudo"],
        "politica": bruto["custo_politica_curva"],
        "economia_vs_defender": bruto["economia_politica_curva"],
        "economia_pct": bruto["economia_pct_curva"],
        "pct_acordo": bruto["share_acordo"],
        "politica_versao": bruto["politica_versao"],
        "modelo_versao": bruto["modelo_versao"],
    }


def _py(v: Any) -> Any:
    if isinstance(v, (list, dict)):
        return v
    if v is None or pd.isna(v):
        return None
    if isinstance(v, pd.Timestamp):
        return v.isoformat()
    return v.item() if hasattr(v, "item") else v


def _records(df: pd.DataFrame) -> list[dict[str, Any]]:
    return [{k: _py(v) for k, v in linha.items()} for linha in df.to_dict(orient="records")]


def _df(db: Session, q: Select) -> pd.DataFrame:
    return pd.read_sql(q, db.connection())


def base_decisoes(db: Session, desde: datetime | None, escritorio_id: int | None = None) -> pd.DataFrame:
    q = (
        select(
            Decisao.id.label("decisao_id"), Decisao.created_at, Decisao.tipo, Decisao.aderente,
            Decisao.tipo_desvio, Decisao.status, Decisao.tempo_analise_s, Decisao.justificativa,
            Decisao.valor_proposto, Decisao.documentos_abertos, Decisao.resultado,
            Decisao.valor_final, Decisao.resultado_em, Decisao.usuario_id,
            Usuario.nome.label("advogado"), Escritorio.id.label("escritorio_id"),
            Escritorio.nome.label("escritorio"), Processo.id.label("processo_id"), Processo.numero,
            Processo.uf, Processo.valor_causa, Recomendacao.tipo.label("rec_tipo"),
            Recomendacao.valor_sugerido, Recomendacao.valor_min, Recomendacao.valor_max,
            Recomendacao.custo_esperado_defesa, Recomendacao.custo_esperado_acordo,
            Recomendacao.economia_esperada, Recomendacao.politica_id,
            ParecerJustificativa.conteudo.label("parecer_ia"),
        )
        .join(Usuario, Usuario.id == Decisao.usuario_id)
        .join(Processo, Processo.id == Decisao.processo_id)
        .join(Escritorio, Escritorio.id == Processo.escritorio_id)
        .join(Recomendacao, Recomendacao.id == Decisao.recomendacao_id)
        .outerjoin(ParecerJustificativa, ParecerJustificativa.decisao_id == Decisao.id)
        .order_by(Decisao.created_at)
    )
    if desde is not None:
        q = q.where(Decisao.created_at >= desde)
    if escritorio_id is not None:
        q = q.where(Processo.escritorio_id == escritorio_id)
    df = _df(db, q)
    if len(df):
        inicio = df["created_at"] - pd.to_timedelta(df["created_at"].dt.weekday, unit="D")
        df["semana"] = inicio.dt.strftime("%Y-%m-%d")
    return df


def _grupo_aderencia(df: pd.DataFrame, chaves: list[str]) -> list[dict[str, Any]]:
    agg = df.groupby(chaves).agg(
        total=("decisao_id", "size"), aderentes=("aderente", "sum"), pct_aderente=("aderente", "mean"),
        tempo_medio_s=("tempo_analise_s", "mean"),
        pct_acordo=("tipo", lambda s: float((s == "acordo").mean())),
    ).reset_index()
    return _records(agg.sort_values(chaves))


def aderencia(db: Session, escritorio_id: int | None = None, desde: datetime | None = None) -> dict:
    df = base_decisoes(db, desde, escritorio_id)
    total = len(df)
    if total == 0:
        return {"total": 0, "aderentes": 0, "pct_aderente": None, "pct_desvio_tipo": None,
                "pct_desvio_valor": None, "tempo_medio_s": None, "pendentes_aprovacao": 0,
                "pct_sem_ver_recomendacao": None, "pct_sem_abrir_documento": None,
                "pct_acordo": None, "por_escritorio": [], "por_advogado": [], "por_semana": [],
                "justificativas": []}

    ev = _df(db, select(Evento.processo_id, Evento.usuario_id, Evento.tipo).where(
        Evento.tipo.in_(["viu_recomendacao", "abriu_documento"])))
    viu = set(zip(ev.loc[ev.tipo == "viu_recomendacao", "processo_id"],
                  ev.loc[ev.tipo == "viu_recomendacao", "usuario_id"], strict=True))
    abriu = set(zip(ev.loc[ev.tipo == "abriu_documento", "processo_id"],
                    ev.loc[ev.tipo == "abriu_documento", "usuario_id"], strict=True))
    pares = list(zip(df["processo_id"], df["usuario_id"], strict=True))
    df["viu_rec"] = [par in viu for par in pares]
    df["abriu_doc"] = [
        par in abriu or bool(docs) for par, docs in zip(pares, df["documentos_abertos"], strict=True)
    ]
    desvios = df[~df["aderente"]].sort_values("created_at", ascending=False).head(20)
    return {
        "total": total,
        "aderentes": int(df["aderente"].sum()),
        "pct_aderente": float(df["aderente"].mean()),
        "pct_desvio_tipo": float((df["tipo_desvio"] == "tipo").mean()),
        "pct_desvio_valor": float((df["tipo_desvio"] == "valor").mean()),
        "tempo_medio_s": _py(df["tempo_analise_s"].mean()),
        "pendentes_aprovacao": int((df["status"] == "pendente_aprovacao").sum()),
        "pct_sem_ver_recomendacao": float((~df["viu_rec"]).mean()),
        "pct_sem_abrir_documento": float((~df["abriu_doc"]).mean()),
        "pct_acordo": float((df["tipo"] == "acordo").mean()),
        "por_escritorio": _grupo_aderencia(df, ["escritorio"]),
        "por_advogado": _grupo_aderencia(df, ["advogado", "escritorio"]),
        "por_semana": _grupo_aderencia(df, ["semana"]),
        "justificativas": _records(desvios[[
            "decisao_id", "created_at", "numero", "processo_id", "advogado", "escritorio", "tipo",
            "rec_tipo", "valor_proposto", "valor_sugerido", "tipo_desvio", "status", "justificativa",
            "parecer_ia",
        ]]),
    }


def _grupo_efetividade(df: pd.DataFrame, chave: str) -> list[dict[str, Any]]:
    if df.empty:
        return []
    agg = df.groupby(chave).agg(
        n=("decisao_id", "size"), taxa_aceite=("aceito", "mean"),
        economia_realizada=("economia_realizada", "sum"), valor_final_medio=("valor_final", "mean"),
    ).reset_index()
    return _records(agg.sort_values(chave))


def efetividade(
    db: Session, desde: datetime | None, politica: Politica | None, info: ModeloInfo
) -> dict[str, Any]:
    df = base_decisoes(db, desde)
    prm = params_de(politica) if politica else None
    op = prm.custo_operacional_acordo if prm else 0.0
    acordos = df[df["tipo"] == "acordo"] if len(df) else df
    com_res = acordos[acordos["resultado"].notna() & (acordos["resultado"] != "seguiu_defesa")].copy()
    if len(com_res):
        com_res["aceito"] = com_res["resultado"].isin(ACEITES)
        custo_real = com_res["valor_final"].fillna(0.0).where(
            com_res["aceito"], com_res["custo_esperado_defesa"]) + op
        com_res["economia_realizada"] = com_res["custo_esperado_defesa"] - custo_real
    aceitos = com_res[com_res["aceito"]] if len(com_res) else com_res
    com_valor = aceitos[aceitos["valor_sugerido"] > 0] if len(aceitos) else aceitos
    cobertura = len(com_res) / len(acordos) if len(acordos) else None
    return {
        "n_decisoes": len(df),
        "n_acordos": len(acordos),
        "n_defesas": int((df["tipo"] == "defesa").sum()) if len(df) else 0,
        "n_com_resultado": len(com_res),
        "n_sem_resultado": len(acordos) - len(com_res),
        "cobertura_resultados": cobertura,
        "taxa_aceite_preliminar": cobertura is not None and cobertura < COBERTURA_CONFIAVEL,
        "taxa_aceite_real": float(com_res["aceito"].mean()) if len(com_res) else None,
        "taxa_aceite_esperada": prm.taxa_aceite_esperada if prm else None,
        "desconto_real": _py((com_valor["valor_final"] / com_valor["valor_sugerido"]).mean())
        if len(com_valor) else None,
        "ticket_medio_final": _py(aceitos["valor_final"].mean()) if len(aceitos) else None,
        "economia_esperada": float(acordos["economia_esperada"].sum()) if len(acordos) else 0.0,
        "economia_realizada": float(com_res["economia_realizada"].sum()) if len(com_res) else 0.0,
        "por_resultado": {str(k): int(v) for k, v in df["resultado"].value_counts().items()}
        if len(df) else {},
        "por_uf": _grupo_efetividade(com_res, "uf"),
        "por_escritorio": _grupo_efetividade(com_res, "escritorio"),
        "por_semana": _grupo_efetividade(com_res, "semana"),
        "backtest_potencial": backtest_potencial(),
        "politica": None if politica is None else {
            "id": politica.id, "versao": politica.versao, "nome": politica.nome,
            "publicada_em": politica.publicada_em, "resumo_backtest": politica.resumo_backtest,
        },
        "modelo": info.model_dump(mode="json"),
    }
