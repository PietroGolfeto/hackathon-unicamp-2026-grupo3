"""Políticas (simular/ativar), dashboards, aprovações e o link de demo."""

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from core.politica import PoliticaParams
from fastapi.testclient import TestClient


def historico_sintetico(n: int = 400, seed: int = 7) -> pd.DataFrame:
    rnd = np.random.default_rng(seed)
    flags = {f: rnd.random(n) < p for f, p in [("contrato", 0.6), ("extrato", 0.6),
             ("comprovante_credito", 0.5), ("dossie", 0.5), ("demonstrativo_divida", 0.5),
             ("laudo_referenciado", 0.5)]}
    n_docs = sum(v.astype(int) for v in flags.values())
    p = np.clip(0.03 + 0.16 * n_docs, 0.01, 0.99)
    perdeu = rnd.random(n) > p
    causa = rnd.uniform(1000, 31000, n).round(2)
    return pd.DataFrame({
        "numero": [f"{i:07d}-00.2025.8.13.{i % 9999:04d}" for i in range(n)],
        "uf": rnd.choice(["MG", "SP", "AM"], n), "sub_assunto": rnd.choice(["Golpe", "Genérico"], n),
        "valor_causa": causa, "resultado_macro": (~perdeu).astype(int),
        "resultado_micro": np.where(perdeu, "Procedência", rnd.choice(["Improcedência", "Extinção"], n)),
        "valor_condenacao": np.where(perdeu, 0.74 * causa, np.nan), **flags,
        "p_exito_oof": p, "condenacao_p20_oof": 0.55 * causa, "condenacao_p50_oof": 0.74 * causa,
        "condenacao_p80_oof": 0.86 * causa, "fold": 0, "scores_origem": "stub",
    })


def test_simular_sem_historico_503(gestor: TestClient):
    r = gestor.post("/api/politicas/simular", json={"params": PoliticaParams().model_dump()})
    assert r.status_code == 503 and "make historico" in r.json()["detail"]


def test_carga_do_historico_e_simulacao(gestor: TestClient, anon: TestClient, app_pronto):
    from app.db import engine
    from app.services import historico

    assert historico.gravar(engine, historico_sintetico()) == 400
    assert anon.post("/api/internal/reload-historico").status_code == 401
    r = anon.post("/api/internal/reload-historico", headers={"X-Internal-Token": "teste-secreto"})
    assert r.status_code == 200 and r.json()["historico_linhas"] == 400
    assert app_pronto.state.modelo.info().n_treino == 400

    r = gestor.post("/api/politicas/simular", json={"params": PoliticaParams().model_dump()})
    assert r.status_code == 200, r.text
    b = r.json()
    assert b["n"] == 400 and 0 < b["pct_acordo"] < 1
    assert b["totais"]["politica"] <= b["totais"]["defender_tudo"]
    assert b["economia_vs_defender"]["valor"] >= 0 and b["tempo_ms"] < 500
    assert {x["uf"] for x in b["por_uf"]} == {"MG", "SP", "AM"} and b["por_n_docs"]
    assert b["hipoteses"]["taxa_aceite_esperada"] == 0.65

    sem_ext = gestor.post("/api/politicas/simular", json={
        "params": PoliticaParams(incluir_extincao_no_backtest=False).model_dump()}).json()
    assert sem_ext["n"] < 400

    r = gestor.post("/api/politicas/simular", json={"params": {"limiar_acordo_forte": 0.9}})
    assert r.status_code == 422


def test_publicar_politica_nova_muda_recomendacoes_futuras(gestor: TestClient, adv: TestClient, exemplos):
    from app.models import Recomendacao as RecModel  # noqa: F401 - garante import do modelo

    ativa = gestor.get("/api/politicas/ativa").json()
    assert ativa["versao"] == 1 and ativa["ativa"]
    antes = adv.get(f"/api/processos/{exemplos['0801234-56.2024.8.10.0001']}/recomendacao").json()

    nova = gestor.post("/api/politicas", json={
        "nome": "Mais agressiva", "params": PoliticaParams(limiar_defesa_forte=1.0,
                                                          limiar_acordo_forte=0.995).model_dump()})
    assert nova.status_code == 201 and nova.json()["ativa"] is False and nova.json()["versao"] == 2
    r = gestor.post(f"/api/politicas/{nova.json()['id']}/ativar")
    assert r.status_code == 200 and r.json()["ativa"] and r.json()["resumo_backtest"]["n"] == 400
    assert gestor.get("/api/politicas/ativa").json()["versao"] == 2
    versoes = gestor.get("/api/politicas").json()
    assert [p["ativa"] for p in versoes] == [True, False]

    depois = adv.get(f"/api/processos/{exemplos['0801234-56.2024.8.10.0001']}/recomendacao").json()
    assert depois["politica_id"] != antes["politica_id"] and depois["tipo"] == "acordo"
    # a decisão já registrada continua apontando para a recomendação antiga
    detalhe = adv.get(f"/api/processos/{exemplos['0801234-56.2024.8.10.0001']}").json()
    assert detalhe["decisao_atual"]["recomendacao_id"] == antes["id"]


def test_aprovacoes(gestor: TestClient, exemplos):
    pend = gestor.get("/api/aprovacoes").json()
    assert pend and pend[0]["numero"] == "0801234-56.2024.8.10.0001"
    assert pend[0]["recomendacao"]["tipo"] == "defesa" and pend[0]["escritorio"] == "Escritório A"
    did = pend[0]["decisao"]["id"]
    r = gestor.post(f"/api/aprovacoes/{did}", json={"acao": "aprovar", "comentario": "ok"})
    assert r.status_code == 200 and r.json()["status"] == "aprovada"
    assert gestor.post(f"/api/aprovacoes/{did}", json={"acao": "rejeitar"}).status_code == 409
    assert all(a["decisao"]["id"] != did for a in gestor.get("/api/aprovacoes").json())


def test_dashboards(gestor: TestClient, exemplos):
    a = gestor.get("/api/dashboard/aderencia").json()
    assert a["total"] >= 2 and 0 <= a["pct_aderente"] <= 1
    assert a["por_escritorio"][0]["escritorio"] == "Escritório A"
    assert a["justificativas"] and a["justificativas"][0]["justificativa"]
    assert a["por_semana"] and a["por_advogado"]
    e = gestor.get("/api/dashboard/efetividade").json()
    assert e["n_acordos"] >= 2 and e["n_com_resultado"] >= 1
    assert e["n_sem_resultado"] == e["n_acordos"] - e["n_com_resultado"]
    assert e["cobertura_resultados"] == e["n_com_resultado"] / e["n_acordos"]
    assert e["taxa_aceite_real"] == 1.0 and e["taxa_aceite_esperada"] == 0.65
    assert e["por_resultado"]["contraproposta_aceita"] == 1
    assert e["backtest_potencial"]["defender_tudo"] > e["backtest_potencial"]["politica"]
    assert e["backtest_potencial"]["n_casos"] == 60000
    assert e["politica"]["versao"] == 2 and e["modelo"]["versao"].startswith("stub")
    filtrado = gestor.get("/api/dashboard/aderencia", params={"escritorio_id": 999}).json()
    assert filtrado["total"] == 0 and filtrado["pct_aderente"] is None


def test_parecer_ia_e_gerado_uma_vez_e_persistido(
    gestor: TestClient, adv: TestClient, exemplos: dict[str, int], monkeypatch
):
    """O parecer consultivo usa o provedor uma vez e depois retorna o cache persistido."""
    from app.services import parecer_ia

    chamadas = 0

    def responder(_contexto: dict[str, Any]) -> dict[str, Any]:
        """Retorne um parecer fixo e conte chamadas ao provedor."""
        nonlocal chamadas
        chamadas += 1
        return {
            "classificacao": "fundamentada",
            "resumo": "A justificativa cita uma evidência concreta do caso.",
            "pontos": ["Evidência específica"],
            "confianca": 0.91,
        }

    monkeypatch.setattr(parecer_ia, "_chamar_openai", responder)
    processo_id = exemplos["0654321-09.2024.8.04.0001"]
    recomendacao = adv.get(f"/api/processos/{processo_id}/recomendacao").json()
    tipo_divergente = "acordo" if recomendacao["tipo"] == "defesa" else "defesa"
    decisao = adv.post(
        f"/api/processos/{processo_id}/decisoes",
        json={
            "tipo": tipo_divergente,
            "valor_proposto": 1500 if tipo_divergente == "acordo" else None,
            "justificativa": "O extrato indica crédito em conta de terceiro.",
        },
    ).json()["decisao"]
    url = f"/api/dashboard/desvios/{decisao['id']}/parecer"
    primeiro = gestor.post(url)
    segundo = gestor.post(url)

    assert primeiro.status_code == 200
    assert segundo.json() == primeiro.json()
    assert chamadas == 1
    desvios = gestor.get("/api/dashboard/aderencia").json()["justificativas"]
    assert next(j for j in desvios if j["decisao_id"] == decisao["id"])["parecer_ia"]


def test_seed_demo_cria_so_processos_pendentes(app_pronto, gestor: TestClient):
    """Nada simulado entra no painel: decisões, eventos e resultados só vêm do portal."""
    from sqlalchemy import func, select

    from app.db import SessionLocal
    from app.models import Decisao, Evento, Processo
    from app.services import seed_demo

    SINTETICOS = Path(__file__).resolve().parents[3] / "data" / "exemplos" / "sinteticos_processos.csv"
    antes = gestor.get("/api/dashboard/aderencia").json()
    with SessionLocal() as db:
        n_dec = db.scalar(select(func.count()).select_from(Decisao))
        n_ev = db.scalar(select(func.count()).select_from(Evento))
        r1 = seed_demo.rodar(db, SINTETICOS, app_pronto.state.modelo)
        assert r1 == {"processos_criados": 340}
        r2 = seed_demo.rodar(db, SINTETICOS, app_pronto.state.modelo)
        assert r2 == {"processos_criados": 0}
        assert db.scalar(select(func.count()).select_from(Decisao)) == n_dec
        assert db.scalar(select(func.count()).select_from(Evento)) == n_ev
        sint = list(db.scalars(select(Processo).where(Processo.origem == "sintetico")))
        assert len(sint) == 340
        assert all(p.status == "pendente" and p.dados_extraidos is None and p.analise is None
                   for p in sint)
        assert all(p.scores["origem"] == "stub" for p in sint)
    depois = gestor.get("/api/dashboard/aderencia").json()
    assert depois["total"] == antes["total"]


def test_mock_painel_enche_o_painel_sem_tocar_na_banca(app_pronto, gestor: TestClient):
    """A exceção de desenvolvimento à decisão 28 preserva o pool da banca e é coerente."""
    from sqlalchemy import select

    from app.db import SessionLocal
    from app.models import Decisao, Escritorio, Processo
    from app.services import mock_painel

    antes = gestor.get("/api/dashboard/aderencia").json()["total"]
    with SessionLocal() as db:
        demo_id = db.scalar(select(Escritorio.id).where(Escritorio.nome == "Banca Demo"))
        resumo = mock_painel.rodar(db, app_pronto.state.modelo, n=60)
        assert resumo["decisoes"] == 60 and 0 < resumo["divergentes"] < 60
        criadas = list(db.scalars(select(Decisao).order_by(Decisao.id.desc()).limit(60)))
        assert all(d.justificativa for d in criadas if not d.aderente)
        assert all(d.tipo_desvio != "nenhum" for d in criadas if not d.aderente)
        assert all(d.tipo == "acordo" for d in criadas if d.resultado)
        assert all(d.resultado_em > d.created_at for d in criadas if d.resultado)
        reservados = db.scalars(select(Processo).where(Processo.escritorio_id == demo_id))
        assert all(p.status == "pendente" for p in reservados)

    depois = gestor.get("/api/dashboard/aderencia").json()
    assert depois["total"] == antes + 60
    assert len(depois["por_semana"]) > 1 and len(depois["por_escritorio"]) > 1
    assert gestor.get("/api/dashboard/efetividade").json()["n_com_resultado"] >= 1


def test_demo_reserva_casos_distintos(anon: TestClient, app_pronto):
    assert anon.get("/api/demo", params={"t": "errado"}, follow_redirects=False).status_code == 403
    c1 = TestClient(app_pronto)
    r1 = c1.get("/api/demo", params={"t": "token-demo"}, follow_redirects=False)
    assert r1.status_code == 303 and r1.headers["location"].startswith("/casos/")
    assert "sessao" in r1.cookies
    c2 = TestClient(app_pronto)
    r2 = c2.get("/api/demo", params={"t": "token-demo"}, follow_redirects=False)
    assert r2.headers["location"] != r1.headers["location"]
    pid = int(r1.headers["location"].rsplit("/", 1)[1])
    caso = c1.get(f"/api/processos/{pid}").json()
    assert caso["escritorio"] == "Banca Demo" and caso["reservado_ate"]
    assert c1.get("/api/auth/me").json()["email"] == "demo@banca-demo"
