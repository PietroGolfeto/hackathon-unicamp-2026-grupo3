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


class ExtratorDuble:
    """Extrator que devolve uma leitura mínima, sem PDF nem LLM."""

    def extrair(self, processo_dir, numero: str):
        from datetime import UTC, datetime

        from core.docs import DadosExtraidos

        return DadosExtraidos(numero=numero, origem="stub", resumo_fatos="bullet do dublê",
                              valor_causa=42000.0, gerado_em=datetime.now(UTC))

    def analisar(self, caso, dados, scores):
        from core.docs import Analise

        return Analise(numero=caso.numero, origem="stub")

    def redigir(self, caso, dados, rec):  # pragma: no cover - a decisão não entra neste teste
        raise NotImplementedError


def test_fase_1_nao_apaga_o_que_a_leitura_dos_documentos_ja_gravou(app_pronto, tmp_path):
    """A base roda a cada POST; ela nunca pode desfazer a extração de um caso já lido."""
    from sqlalchemy import select

    from app.db import SessionLocal
    from app.models import Escritorio
    from app.services import ingest

    pasta = tmp_path / "exemplos" / "0800001-11.2024.8.10.0001"
    (pasta / "autos").mkdir(parents=True)
    (pasta / "autos" / "peticao_inicial.pdf").write_bytes(b"%PDF-1.4")
    with SessionLocal() as db:
        esc = db.scalar(select(Escritorio).where(Escritorio.nome == "Escritório A"))
        lido = ingest.ingerir_pasta(db, pasta, tmp_path, ExtratorDuble(), app_pronto.state.modelo,
                                    esc.id)
        assert lido.dados_extraidos is not None and lido.valor_causa == 42000.0

        base = ingest.ingerir_base(db, pasta, tmp_path, app_pronto.state.modelo, esc.id)
        assert base.dados_extraidos is not None, "a base sobrescreveu a extração"
        assert base.valor_causa == 42000.0, "a base voltou o valor da causa para o padrão"


def test_processo_sem_p3_nunca_fica_marcado_como_pendente(adv: TestClient, exemplos: dict[str, int]):
    """Sem extrator plugado não há leitura a esperar: a tela não pode ficar em loading eterno."""
    pid = next(iter(exemplos.values()))
    assert adv.get(f"/api/processos/{pid}").json()["extracao_pendente"] is False
    assert all(not p["extracao_pendente"] for p in adv.get("/api/processos").json())
