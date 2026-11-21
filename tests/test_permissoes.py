"""Testa os decoradores de perfil e o escopo por unidade com rotas temporárias."""
import pytest
from flask import jsonify

from app.models import Unidade
from app.security import autenticado, exigir_unidade, perfis_permitidos


@pytest.fixture()
def app_com_rotas(seeded):
    app = seeded

    @app.get("/_t/qualquer")
    @autenticado
    def qualquer():
        return jsonify(ok=True)

    @app.get("/_t/funcionario")
    @perfis_permitidos("FUNCIONARIO")
    def so_funcionario():
        return jsonify(ok=True)

    @app.get("/_t/gerente")
    @perfis_permitidos("GERENTE")
    def so_gerente():
        return jsonify(ok=True)

    @app.get("/_t/matriz")
    @perfis_permitidos("MATRIZ")
    def so_matriz():
        return jsonify(ok=True)

    @app.get("/_t/cliente")
    @perfis_permitidos("CLIENTE")
    def so_cliente():
        return jsonify(ok=True)

    @app.get("/_t/unidade/<int:id_unidade>")
    @perfis_permitidos("GERENTE", "MATRIZ")
    def da_unidade(id_unidade):
        exigir_unidade(id_unidade)
        return jsonify(ok=True)

    return app


def _h(client, login):
    token = client.post("/api/v1/auth/login", json={"login": login, "senha": "senha123"}).get_json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.parametrize("rota,login,esperado", [
    ("/_t/qualquer", "cliente@exemplo.com", 200),
    ("/_t/funcionario", "funcionario", 200),
    ("/_t/funcionario", "gerente", 200),            # gerente herda o que o funcionário faz
    ("/_t/funcionario", "matriz", 403),
    ("/_t/funcionario", "cliente@exemplo.com", 403),
    ("/_t/gerente", "gerente", 200),
    ("/_t/gerente", "funcionario", 403),
    ("/_t/gerente", "matriz", 403),
    ("/_t/matriz", "matriz", 200),
    ("/_t/matriz", "gerente", 403),
    ("/_t/cliente", "cliente@exemplo.com", 200),
    ("/_t/cliente", "gerente", 403),
])
def test_matriz_de_permissoes(app_com_rotas, rota, login, esperado):
    client = app_com_rotas.test_client()
    assert client.get(rota, headers=_h(client, login)).status_code == esperado


def test_rota_protegida_sem_token(app_com_rotas):
    client = app_com_rotas.test_client()
    for rota in ("/_t/qualquer", "/_t/funcionario", "/_t/matriz"):
        r = client.get(rota)
        assert r.status_code == 401
        assert r.get_json()["erro"] == "NAO_AUTENTICADO"


def test_resposta_403_segue_o_padrao(app_com_rotas):
    client = app_com_rotas.test_client()
    r = client.get("/_t/matriz", headers=_h(client, "funcionario"))
    assert r.get_json()["erro"] == "SEM_PERMISSAO"


def test_gerente_so_acessa_a_propria_unidade(app_com_rotas):
    client = app_com_rotas.test_client()
    propria = Unidade.query.filter_by(tipo_cozinha="COMPLETA").one()   # a do gerente no seed
    outra = Unidade.query.filter_by(tipo_cozinha="REDUZIDA").one()
    h = _h(client, "gerente")
    assert client.get(f"/_t/unidade/{propria.id}", headers=h).status_code == 200
    r = client.get(f"/_t/unidade/{outra.id}", headers=h)
    assert r.status_code == 403
    assert r.get_json()["erro"] == "SEM_PERMISSAO"


def test_matriz_acessa_qualquer_unidade(app_com_rotas):
    client = app_com_rotas.test_client()
    h = _h(client, "matriz")
    for unidade in Unidade.query.all():
        assert client.get(f"/_t/unidade/{unidade.id}", headers=h).status_code == 200
