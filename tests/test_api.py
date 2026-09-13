from __future__ import annotations

from fastapi.testclient import TestClient

from enteros import config as cfg
from enteros.api.main import app

client = TestClient(app)


def test_saude():
    r = client.get("/saude")
    assert r.status_code == 200 and r.json()["ok"]


def test_recomendacao_caso_02(caso_02):
    r = client.post("/recomendacao", json=caso_02.model_dump())
    assert r.status_code == 200
    corpo = r.json()
    assert corpo["decisao"] == cfg.DECISAO_ACORDO
    assert corpo["escada"]["teto"] < corpo["ev_defesa"]


def test_recomendacao_rejeita_uf_invalida():
    r = client.post("/recomendacao", json={"uf": "ZZ", "valor_causa": 1000})
    assert r.status_code == 422


def test_politica_e_modelo():
    assert client.get("/politica").json()["versao"]
    assert "auc_oof" in client.get("/modelo").json()["metricas"]
