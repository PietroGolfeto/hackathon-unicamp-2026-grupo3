"""Fluxo ponta a ponta do advogado com os dois processos exemplo (StubModelo, sem P3)."""

from fastapi.testclient import TestClient

from app.services.ingest import VALOR_CAUSA_PADRAO

MANAUS = "0654321-09.2024.8.04.0001"
SAO_LUIS = "0801234-56.2024.8.10.0001"


def test_ingest_so_grava_o_que_e_deterministico(adv: TestClient, exemplos: dict[str, int]):
    """UF pelo CNJ e flags pelos nomes dos arquivos; nada é lido de dentro dos documentos."""
    d = adv.get(f"/api/processos/{exemplos[MANAUS]}").json()
    assert d["uf"] == "AM" and d["valor_causa"] == VALOR_CAUSA_PADRAO and d["sub_assunto"] is None
    assert d["dados_extraidos"] is None and d["analise"] is None and d["sinais"] == []
    assert d["subsidios"]["extrato"] and d["subsidios"]["dossie"] and not d["subsidios"]["contrato"]
    assert len(d["documentos"]) == 3 and d["documentos"][0]["url"].startswith("/api/files/")
    assert d["scores"]["origem"] == "stub"

    d2 = adv.get(f"/api/processos/{exemplos[SAO_LUIS]}").json()
    assert d2["uf"] == "MA" and sum(d2["subsidios"].values()) == 6


def test_lista_do_escritorio_e_isolamento(adv: TestClient, adv_b: TestClient, exemplos):
    numeros = {p["numero"] for p in adv.get("/api/processos").json()}
    assert {MANAUS, SAO_LUIS} <= numeros
    assert adv_b.get(f"/api/processos/{exemplos[MANAUS]}").status_code == 403
    assert MANAUS not in {p["numero"] for p in adv_b.get("/api/processos").json()}
    busca = adv.get("/api/processos", params={"busca": "0654321"}).json()
    assert [p["numero"] for p in busca] == [MANAUS]


def test_recomendacao_gravada_e_estavel(adv: TestClient, exemplos):
    r1 = adv.get(f"/api/processos/{exemplos[MANAUS]}/recomendacao").json()
    r2 = adv.get(f"/api/processos/{exemplos[MANAUS]}/recomendacao").json()
    assert r1["id"] == r2["id"]
    assert r1["tipo"] == "acordo" and r1["regra"] == "custo"  # 2 de 6 subsídios, sem sinais
    assert r1["sinais_acionados"] == []
    assert len(r1["motivos"]) == 3 and r1["valor_min"] < r1["valor_sugerido"] < r1["valor_max"]

    forte = adv.get(f"/api/processos/{exemplos[SAO_LUIS]}/recomendacao").json()
    assert forte["tipo"] == "defesa" and forte["valor_sugerido"] is None


def test_arquivo_abre_e_registra_evento(adv: TestClient, exemplos):
    r = adv.get(f"/api/files/{exemplos[MANAUS]}/peticao_inicial.txt")
    assert r.status_code == 200 and "Arquivo de exemplo" in r.text
    assert adv.get(f"/api/files/{exemplos[MANAUS]}/nao_existe.pdf").status_code == 404
    assert adv.get(f"/api/files/{exemplos[MANAUS]}/../../etc/passwd").status_code in (404, 422)


def test_decisao_divergente_exige_justificativa(adv: TestClient, exemplos):
    pid = exemplos[MANAUS]
    r = adv.post(f"/api/processos/{pid}/decisoes", json={"tipo": "defesa", "tempo_analise_s": 30})
    assert r.status_code == 422 and "justificativa" in r.json()["detail"]
    r = adv.post(f"/api/processos/{pid}/decisoes", json={"tipo": "acordo"})
    assert r.status_code == 422 and "valor" in r.json()["detail"]


def test_decisao_aderente_sem_minutas_nem_contato_sem_p3(adv: TestClient, exemplos):
    pid = exemplos[MANAUS]
    rec = adv.get(f"/api/processos/{pid}/recomendacao").json()
    r = adv.post(f"/api/processos/{pid}/decisoes", json={
        "tipo": "acordo", "valor_proposto": rec["valor_sugerido"], "tempo_analise_s": 240,
        "documentos_abertos": ["peticao_inicial.txt"],
    })
    assert r.status_code == 201, r.text
    corpo = r.json()
    assert corpo["decisao"]["aderente"] is True and corpo["decisao"]["status"] == "registrada"
    assert corpo["decisao"]["recomendacao_id"] == rec["id"]
    assert corpo["minutas"] is None and corpo["contato_adverso"] is None
    assert adv.get(f"/api/processos/{pid}").json()["status"] == "decidido"

    res = adv.post(f"/api/decisoes/{corpo['decisao']['id']}/resultado",
                   json={"resultado": "aceito"})
    assert res.status_code == 422
    res = adv.post(f"/api/decisoes/{corpo['decisao']['id']}/resultado",
                   json={"resultado": "contraproposta_aceita", "valor_final": rec["valor_min"]})
    assert res.status_code == 200 and res.json()["valor_final"] == rec["valor_min"]
    assert adv.get(f"/api/processos/{pid}").json()["status"] == "encerrado"


def test_decisao_fora_da_banda_vai_para_aprovacao(adv: TestClient, exemplos):
    pid = exemplos[SAO_LUIS]  # recomendação: defesa
    r = adv.post(f"/api/processos/{pid}/decisoes", json={
        "tipo": "acordo", "valor_proposto": 2000, "justificativa": "Autor aceitou valor baixo.",
    })
    assert r.status_code == 201
    d = r.json()["decisao"]
    assert d["aderente"] is False and d["tipo_desvio"] == "tipo"
    assert d["status"] == "pendente_aprovacao"


def test_eventos_e_resumo_txt(adv: TestClient, exemplos):
    pid = exemplos[MANAUS]
    r = adv.post("/api/eventos", json={"processo_id": pid, "tipo": "abriu_documento",
                                       "payload": {"arquivo": "dossie.txt"}})
    assert r.status_code == 204
    txt = adv.get(f"/api/processos/{pid}/resumo.txt")
    assert txt.status_code == 200 and "RECOMENDAÇÃO: ACORDO" in txt.text and MANAUS in txt.text
