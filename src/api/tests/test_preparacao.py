"""A tela do advogado dispara a preparação e espera; o endpoint precisa ser idempotente."""

from __future__ import annotations

import time

from conftest import DADOS
from fastapi.testclient import TestClient

NUMEROS = {p.name for p in (DADOS / "exemplos").iterdir() if p.is_dir()}
PASTAS = len(NUMEROS)


def aguardar(cliente: TestClient, tentativas: int = 60) -> dict:
    for _ in range(tentativas):
        estado = cliente.get("/api/preparacao").json()
        if estado["status"] in ("pronto", "erro"):
            return estado
        time.sleep(0.1)
    raise AssertionError("preparação não terminou a tempo")


def test_preparar_processa_as_pastas_e_e_idempotente(adv: TestClient):
    r = adv.post("/api/preparacao")
    assert r.status_code == 202, r.text
    assert r.json()["status"] in ("rodando", "pronto")

    estado = aguardar(adv)
    # sem P3 plugado (EXTRACTOR_IMPL inválido no conftest) nada é inferido dos PDFs, mas os
    # scores e a recomendação existem: a tela tem o que mostrar e não fica em loading eterno.
    assert estado["status"] == "pronto", estado
    assert estado["total"] == PASTAS and estado["prontos"] == PASTAS

    numeros = [p["numero"] for p in adv.get("/api/processos").json()]
    assert NUMEROS <= set(numeros)

    de_novo = adv.post("/api/preparacao")
    assert de_novo.status_code == 202 and de_novo.json()["status"] == "pronto"
    # idempotente: preparar de novo não duplica nem cria processo novo
    assert [p["numero"] for p in adv.get("/api/processos").json()] == numeros


def test_preparacao_deixa_a_recomendacao_pronta_na_lista(adv: TestClient):
    adv.post("/api/preparacao")
    aguardar(adv)
    preparados = [p for p in adv.get("/api/processos").json() if p["numero"] in NUMEROS]
    assert len(preparados) == PASTAS
    assert all(p["recomendacao"] is not None for p in preparados)


def test_preparacao_exige_sessao(anon: TestClient):
    assert anon.get("/api/preparacao").status_code == 401
