import pytest

from app.models import Produto, Sabor
from tests.helpers import cabecalho

B = "/api/v1"


def _produto(nome="Tapioca"):
    return Produto.query.filter_by(nome=nome).one()


# ---------- POST /produtos ----------
def test_matriz_cria_produto(seeded, client):
    r = client.post(f"{B}/produtos", json={"nome": "Pamonha", "descricao": "Pamonha doce"}, headers=cabecalho(client, "matriz"))
    assert r.status_code == 201
    assert r.get_json()["nome"] == "Pamonha"


def test_produto_duplicado_ignora_maiusculas(seeded, client):
    r = client.post(f"{B}/produtos", json={"nome": "TAPIOCA"}, headers=cabecalho(client, "matriz"))
    assert r.status_code == 409 and r.get_json()["erro"] == "PRODUTO_DUPLICADO"


@pytest.mark.parametrize("login,esperado", [("gerente", 403), ("funcionario", 403), ("cliente@exemplo.com", 403)])
def test_so_a_matriz_cria_produto(seeded, client, login, esperado):
    r = client.post(f"{B}/produtos", json={"nome": "Pamonha"}, headers=cabecalho(client, login))
    assert r.status_code == esperado


def test_produto_sem_nome(seeded, client):
    r = client.post(f"{B}/produtos", json={"descricao": "sem nome"}, headers=cabecalho(client, "matriz"))
    assert r.status_code == 400
    assert r.get_json()["detalhes"][0]["campo"] == "nome"


# ---------- POST /produtos/{id}/sabores ----------
def test_matriz_cria_sabor_com_periodo_sazonal(seeded, client):
    corpo = {"nome": "Canjica", "preco_base": 6.5, "data_inicio_venda": "2026-06-01", "data_fim_venda": "2026-07-31"}
    r = client.post(f"{B}/produtos/{_produto('Suco regional').id}/sabores", json=corpo, headers=cabecalho(client, "matriz"))
    assert r.status_code == 201
    saida = r.get_json()
    assert saida["preco_base"] == 6.5 and saida["data_inicio_venda"] == "2026-06-01"


def test_sabor_sem_periodo_e_vendido_o_ano_todo(seeded, client):
    r = client.post(f"{B}/produtos/{_produto().id}/sabores", json={"nome": "Coco", "preco_base": 6},
                    headers=cabecalho(client, "matriz"))
    assert r.status_code == 201
    assert r.get_json()["data_inicio_venda"] is None and r.get_json()["data_fim_venda"] is None


@pytest.mark.parametrize("corpo", [
    {"nome": "Coco", "preco_base": -3},
    {"nome": "Coco", "preco_base": 0},
    {"nome": "Coco", "preco_base": "caro"},
    {"nome": "Coco"},
    {"preco_base": 5},
    {"nome": "Coco", "preco_base": 5, "data_inicio_venda": "2026-08-01", "data_fim_venda": "2026-06-01"},
    {"nome": "Coco", "preco_base": 5, "data_inicio_venda": "01/06/2026"},
])
def test_sabor_dados_invalidos(seeded, client, corpo):
    r = client.post(f"{B}/produtos/{_produto().id}/sabores", json=corpo, headers=cabecalho(client, "matriz"))
    assert r.status_code == 400 and r.get_json()["erro"] == "DADOS_INVALIDOS"


def test_sabor_repetido_no_mesmo_produto_e_barrado_mas_em_outro_produto_nao(seeded, client):
    h = cabecalho(client, "matriz")
    r = client.post(f"{B}/produtos/{_produto().id}/sabores", json={"nome": "queijo", "preco_base": 5}, headers=h)
    assert r.status_code == 409 and r.get_json()["erro"] == "SABOR_DUPLICADO"
    r = client.post(f"{B}/produtos/{_produto('Cuscuz recheado').id}/sabores", json={"nome": "Queijo", "preco_base": 9}, headers=h)
    assert r.status_code == 201


def test_sabor_em_produto_inexistente(seeded, client):
    r = client.post(f"{B}/produtos/9999/sabores", json={"nome": "Coco", "preco_base": 5}, headers=cabecalho(client, "matriz"))
    assert r.status_code == 404 and r.get_json()["erro"] == "PRODUTO_NAO_ENCONTRADO"


def test_gerente_nao_cria_sabor(seeded, client):
    r = client.post(f"{B}/produtos/{_produto().id}/sabores", json={"nome": "Coco", "preco_base": 5}, headers=cabecalho(client, "gerente"))
    assert r.status_code == 403


# ---------- PUT /sabores/{id} ----------
def test_atualizar_preco_do_sabor(seeded, client):
    queijo = Sabor.query.filter_by(nome="Queijo").one()
    r = client.put(f"{B}/sabores/{queijo.id}", json={"preco_base": 5.5}, headers=cabecalho(client, "matriz"))
    assert r.status_code == 200
    assert r.get_json()["preco_base"] == 5.5 and r.get_json()["nome"] == "Queijo"


def test_atualizar_periodo_do_sabor_e_remover_sazonalidade(seeded, client):
    junino = Sabor.query.filter_by(nome="Bolo de milho (junino)").one()
    h = cabecalho(client, "matriz")
    r = client.put(f"{B}/sabores/{junino.id}", json={"data_inicio_venda": None, "data_fim_venda": None}, headers=h)
    assert r.status_code == 200
    assert r.get_json()["data_inicio_venda"] is None and r.get_json()["data_fim_venda"] is None


def test_atualizar_periodo_incoerente_com_o_que_ja_existe(seeded, client):
    junino = Sabor.query.filter_by(nome="Bolo de milho (junino)").one()  # termina em 31/07
    r = client.put(f"{B}/sabores/{junino.id}", json={"data_inicio_venda": f"{junino.data_fim_venda.year}-08-15"},
                   headers=cabecalho(client, "matriz"))
    assert r.status_code == 400 and r.get_json()["erro"] == "PERIODO_INVALIDO"


def test_atualizar_nome_do_sabor_para_um_ja_existente(seeded, client):
    presunto = Sabor.query.filter_by(nome="Queijo com presunto").one()
    r = client.put(f"{B}/sabores/{presunto.id}", json={"nome": "Queijo"}, headers=cabecalho(client, "matriz"))
    assert r.status_code == 409


def test_atualizar_sabor_inexistente_sem_permissao_e_sem_campos(seeded, client):
    h = cabecalho(client, "matriz")
    assert client.put(f"{B}/sabores/9999", json={"preco_base": 5}, headers=h).status_code == 404
    queijo = Sabor.query.filter_by(nome="Queijo").one()
    assert client.put(f"{B}/sabores/{queijo.id}", json={}, headers=h).status_code == 400
    assert client.put(f"{B}/sabores/{queijo.id}", json={"preco_base": 9}, headers=cabecalho(client, "gerente")).status_code == 403
    assert client.put(f"{B}/sabores/{queijo.id}", json={"preco_base": 9}).status_code == 401


def test_sabor_unico_por_produto_tambem_no_banco(seeded):
    from sqlalchemy.exc import IntegrityError
    from app.extensions import db
    tapioca = _produto()
    db.session.add(Sabor(id_produto=tapioca.id, nome="Queijo", preco_base=1))
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()
