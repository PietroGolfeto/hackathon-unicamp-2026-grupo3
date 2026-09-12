"""API mínima que a tela do advogado e o painel do banco consomem. Sem banco de dados nesta fase."""

from __future__ import annotations

import json

from fastapi import FastAPI, HTTPException

from enteros import config as cfg
from enteros.policy.engine import engine_padrao
from enteros.schemas import CaseFeatures, Recomendacao

app = FastAPI(title="Política de Acordos — Banco Unicamp (Grupo 3)", version="0.1.0")


@app.get("/saude")
def saude() -> dict:
    eng = engine_padrao()
    return {"ok": True, "politica": eng.politica.versao, "modelo": eng.modelo.versao}


@app.post("/recomendacao", response_model=Recomendacao)
def recomendacao(caso: CaseFeatures) -> Recomendacao:
    return engine_padrao().recomendar(caso)


@app.get("/politica")
def politica() -> dict:
    return engine_padrao().politica.model_dump()


@app.get("/modelo")
def modelo() -> dict:
    m = engine_padrao().modelo
    return {"versao": m.versao, "metricas": m.metricas, "calibracao": m.calibracao,
            "coeficientes": dict(zip(m.colunas, m.coef)), "intercepto": m.intercepto}


@app.get("/segmentos")
def segmentos() -> dict:
    s = engine_padrao().segmentos
    return {"chave": ["sub_assunto", *cfg.DOCS_PREDITIVOS, "uf"], "p_global": s.p_global, "pais": s.pai, "segmentos": s.seg}


@app.get("/backtest")
def backtest() -> dict:
    if not cfg.ARQ_RESUMO_BACKTEST.exists():
        raise HTTPException(404, "backtest ainda não gerado; rode `make backtest`")
    return json.loads(cfg.ARQ_RESUMO_BACKTEST.read_text(encoding="utf-8"))
