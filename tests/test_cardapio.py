from datetime import date

import pytest

from app.extensions import db
from app.models import ProdutoUnidade, Sabor, Unidade
from tests.helpers import cabecalho

B = "/api/v1"


def _ids(seeded):
    completa = Unidade.query.filter_by(tipo_cozinha="COMPLETA").one()
    reduzida = Unidade.query.filter_by(tipo_cozinha="REDUZIDA").one()
    return completa.id, reduzida.id


def _sabores_do_cardapio(corpo):
    return {s["sabor"] for item in corpo["itens"] for s in item["sabores"]}


# ---------- GET /unidades ----------
def test_listar_unidades_e_publico(seeded, client):
    r = client.get(f"{B}/unidades")
    assert r.status_code == 200
    corpo = r.get_json()
    assert corpo["total"] == 2 and corpo["pagina"] == 1 and corpo["tamanho"] == 20
    assert {u["tipo_cozinha"] for u in corpo["itens"]} == {"COMPLETA", "REDUZIDA"}


def test_listar_unidades_filtros_e_paginacao(seeded, client):
    assert client.get(f"{B}/unidades?cidade=recife").get_json()["total"] == 2
    assert client.get(f"{B}/unidades?cidade=Olinda").get_json()["total"] == 0
    assert client.get(f"{B}/unidades?regiao=LITORAL").get_json()["total"] == 2
    pagina2 = client.get(f"{B}/unidades?tamanho=1&pagina=2").get_json()
    assert len(pagina2["itens"]) == 1 and pagina2["total"] == 2


@pytest.mark.parametrize("consulta", ["pagina=0", "tamanho=0", "tamanho=101", "pagina=abc", "tamanho=-5"])
def test_paginacao_invalida(seeded, client, consulta):
    r = client.get(f"{B}/unidades?{consulta}")
    assert r.status_code == 400
    assert r.get_json()["erro"] == "PARAMETRO_INVALIDO"


# ---------- POST/PUT /unidades ----------
NOVA = {"nome": "Raízes Olinda", "cidade": "Olinda", "regiao": "Litoral", "tipo_cozinha": "REDUZIDA"}


def test_matriz_cria_e_atualiza_unidade(seeded, client):
    h = cabecalho(client, "matriz")
    r = client.post(f"{B}/unidades", json=NOVA, headers=h)
    assert r.status_code == 201
    id_ = r.get_json()["id"]
    r = client.put(f"{B}/unidades/{id_}", json={"tipo_cozinha": "COMPLETA"}, headers=h)
    assert r.status_code == 200
    assert r.get_json()["tipo_cozinha"] == "COMPLETA" and r.get_json()["nome"] == "Raízes Olinda"


@pytest.mark.parametrize("login", ["gerente", "funcionario", "cliente@exemplo.com"])
def test_outros_perfis_nao_criam_unidade(seeded, client, login):
    r = client.post(f"{B}/unidades", json=NOVA, headers=cabecalho(client, login))
    assert r.status_code == 403


def test_criar_unidade_sem_token(seeded, client):
    assert client.post(f"{B}/unidades", json=NOVA).status_code == 401


def test_criar_unidade_dados_invalidos(seeded, client):
    h = cabecalho(client, "matriz")
    r = client.post(f"{B}/unidades", json={"nome": "X", "tipo_cozinha": "GIGANTE"}, headers=h)
    assert r.status_code == 400
    campos = {d["campo"] for d in r.get_json()["detalhes"]}
    assert {"nome", "cidade", "regiao", "tipo_cozinha"} <= campos


def test_atualizar_unidade_inexistente_e_corpo_vazio(seeded, client):
    h = cabecalho(client, "matriz")
    assert client.put(f"{B}/unidades/9999", json={"nome": "Novo nome"}, headers=h).status_code == 404
    completa, _ = _ids(seeded)
    r = client.put(f"{B}/unidades/{completa}", json={}, headers=h)
    assert r.status_code == 400 and r.get_json()["erro"] == "SEM_CAMPOS"


# ---------- GET /unidades/{id}/cardapio ----------
def test_cardapio_depende_da_unidade(seeded, client):
    completa, reduzida = _ids(seeded)
    cheio = _sabores_do_cardapio(client.get(f"{B}/unidades/{completa}/cardapio?data=2026-01-10").get_json())
    enxuto = _sabores_do_cardapio(client.get(f"{B}/unidades/{reduzida}/cardapio?data=2026-01-10").get_json())
    assert {"Ovo com queijo", "Carne de sol"} <= cheio
    assert not {"Ovo com queijo", "Carne de sol"} & enxuto
    assert "Queijo" in enxuto


def test_cardapio_agrupa_por_produto_com_precos(seeded, client):
    completa, _ = _ids(seeded)
    corpo = client.get(f"{B}/unidades/{completa}/cardapio?data=2026-01-10").get_json()
    assert corpo["unidade"]["id"] == completa and corpo["data_referencia"] == "2026-01-10"
    tapioca = next(i for i in corpo["itens"] if i["produto"] == "Tapioca")
    assert {s["sabor"]: s["preco"] for s in tapioca["sabores"]} == {
        "Queijo": 5.0, "Queijo com presunto": 7.0, "Ovo com queijo": 8.0}


def test_sabor_junino_so_aparece_na_epoca(seeded, client):
    completa, _ = _ids(seeded)
    ano = date.today().year
    fora = _sabores_do_cardapio(client.get(f"{B}/unidades/{completa}/cardapio?data={ano}-03-10").get_json())
    dentro = _sabores_do_cardapio(client.get(f"{B}/unidades/{completa}/cardapio?data={ano}-06-15").get_json())
    depois = _sabores_do_cardapio(client.get(f"{B}/unidades/{completa}/cardapio?data={ano}-08-01").get_json())
    assert "Bolo de milho (junino)" not in fora and "Bolo de milho (junino)" not in depois
    assert "Bolo de milho (junino)" in dentro


def test_cardapio_unidade_inexistente_e_data_invalida(seeded, client):
    assert client.get(f"{B}/unidades/9999/cardapio").status_code == 404
    completa, _ = _ids(seeded)
    r = client.get(f"{B}/unidades/{completa}/cardapio?data=10/06/2026")
    assert r.status_code == 400 and r.get_json()["erro"] == "PARAMETRO_INVALIDO"


# ---------- PUT /unidades/{u}/sabores/{s} ----------
def _sabor(nome):
    return Sabor.query.filter_by(nome=nome).one()


def test_gerente_tira_sabor_do_cardapio_da_propria_unidade(seeded, client):
    completa, _ = _ids(seeded)
    queijo = _sabor("Queijo")
    h = cabecalho(client, "gerente")
    r = client.put(f"{B}/unidades/{completa}/sabores/{queijo.id}", json={"esta_disponivel": False}, headers=h)
    assert r.status_code == 200 and r.get_json()["esta_disponivel"] is False
    assert "Queijo" not in _sabores_do_cardapio(client.get(f"{B}/unidades/{completa}/cardapio?data=2026-01-10").get_json())


def test_preco_local_vale_so_na_unidade_e_pode_ser_removido(seeded, client):
    completa, reduzida = _ids(seeded)
    queijo = _sabor("Queijo")
    h = cabecalho(client, "matriz")
    r = client.put(f"{B}/unidades/{completa}/sabores/{queijo.id}", json={"esta_disponivel": True, "preco_local": 5.5}, headers=h)
    assert r.get_json()["preco_vigente"] == 5.5

    def preco(unidade):
        cardapio = client.get(f"{B}/unidades/{unidade}/cardapio?data=2026-01-10").get_json()
        tapioca = next(i for i in cardapio["itens"] if i["produto"] == "Tapioca")
        return next(s["preco"] for s in tapioca["sabores"] if s["sabor"] == "Queijo")

    assert preco(completa) == 5.5 and preco(reduzida) == 5.0
    r = client.put(f"{B}/unidades/{completa}/sabores/{queijo.id}", json={"esta_disponivel": True}, headers=h)
    assert r.get_json()["preco_local"] is None and preco(completa) == 5.0  # sem preco_local volta ao preço base


def test_gerente_adiciona_sabor_novo_na_unidade_e_recebe_201(seeded, client):
    completa, _ = _ids(seeded)
    ovo = _sabor("Ovo com queijo")
    ProdutoUnidade.query.filter_by(id_unidade=completa, id_sabor=ovo.id).delete()
    db.session.commit()
    r = client.put(f"{B}/unidades/{completa}/sabores/{ovo.id}", json={"esta_disponivel": True},
                   headers=cabecalho(client, "gerente"))
    assert r.status_code == 201
    assert ProdutoUnidade.query.filter_by(id_unidade=completa, id_sabor=ovo.id).count() == 1


def test_gerente_nao_mexe_em_outra_unidade(seeded, client):
    _, reduzida = _ids(seeded)
    r = client.put(f"{B}/unidades/{reduzida}/sabores/{_sabor('Queijo').id}", json={"esta_disponivel": False},
                   headers=cabecalho(client, "gerente"))
    assert r.status_code == 403 and r.get_json()["erro"] == "SEM_PERMISSAO"


@pytest.mark.parametrize("login", ["funcionario", "cliente@exemplo.com"])
def test_funcionario_e_cliente_nao_definem_disponibilidade(seeded, client, login):
    completa, _ = _ids(seeded)
    r = client.put(f"{B}/unidades/{completa}/sabores/{_sabor('Queijo').id}", json={"esta_disponivel": False},
                   headers=cabecalho(client, login))
    assert r.status_code == 403


@pytest.mark.parametrize("corpo", [{}, {"esta_disponivel": "talvez"}, {"esta_disponivel": True, "preco_local": -1},
                                    {"esta_disponivel": True, "preco_local": "abc"}, {"esta_disponivel": True, "preco_local": 0}])
def test_disponibilidade_dados_invalidos(seeded, client, corpo):
    completa, _ = _ids(seeded)
    r = client.put(f"{B}/unidades/{completa}/sabores/{_sabor('Queijo').id}", json=corpo, headers=cabecalho(client, "gerente"))
    assert r.status_code == 400 and r.get_json()["erro"] == "DADOS_INVALIDOS"


def test_disponibilidade_sabor_ou_unidade_inexistente(seeded, client):
    completa, _ = _ids(seeded)
    h = cabecalho(client, "matriz")
    r = client.put(f"{B}/unidades/{completa}/sabores/9999", json={"esta_disponivel": True}, headers=h)
    assert r.status_code == 404 and r.get_json()["erro"] == "SABOR_NAO_ENCONTRADO"
    r = client.put(f"{B}/unidades/9999/sabores/{_sabor('Queijo').id}", json={"esta_disponivel": True}, headers=h)
    assert r.status_code == 404 and r.get_json()["erro"] == "UNIDADE_NAO_ENCONTRADA"
