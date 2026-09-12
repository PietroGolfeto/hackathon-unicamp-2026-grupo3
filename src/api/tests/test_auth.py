from fastapi.testclient import TestClient


def test_health(anon: TestClient):
    r = anon.get("/api/health")
    assert r.status_code == 200
    assert r.json()["ok"] is True
    assert r.json()["modelo"].startswith("stub")


def test_me_sem_cookie_401(anon: TestClient):
    assert anon.get("/api/auth/me").status_code == 401


def test_login_errado_401(anon: TestClient):
    r = anon.post("/api/auth/login", json={"email": "adv1@escritorio-a", "senha": "x"})
    assert r.status_code == 401
    assert "inválidos" in r.json()["detail"]


def test_login_me_logout(app_pronto):
    c = TestClient(app_pronto)
    r = c.post("/api/auth/login", json={"email": "GESTOR@banco-ufmg", "senha": "senha123"})
    assert r.status_code == 200
    assert "sessao" in r.cookies
    me = c.get("/api/auth/me").json()
    assert me["papel"] == "gestor" and me["escritorio_id"] is None
    assert c.post("/api/auth/logout").status_code == 204
    c.cookies.clear()
    assert c.get("/api/auth/me").status_code == 401


def test_advogado_nao_acessa_rotas_de_gestor(adv: TestClient):
    assert adv.get("/api/dashboard/aderencia").status_code == 403
    assert adv.get("/api/politicas").status_code == 403
