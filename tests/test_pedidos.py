from datetime import date

import pytest

from app.extensions import db
from app.models import Cliente, ProdutoUnidade
from tests.helpers import (
    B, CLIENTE, cabecalho, cadastrar_cliente, item, novo_funcionario, pagar, pedido_em_producao, pedido_simples, pedir,
    sabor, unidade,
)


# ---------- criação ----------
def test_cliente_cria_pedido_e_o_total_confere(seeded, client):
    r = pedir(client, CLIENTE, [item("Queijo"), item("Queijo com presunto", 2)], canal="APP")
    assert r.status_code == 201
    p = r.get_json()
    assert p["valor_total"] == 19.0  # 5,00 + 2 x 7,00
    assert p["status_codigo"] == "AGUARDANDO_PAGAMENTO" and p["status"] == "Aguardando liberação do pagamento"
    assert p["id_cliente"] == Cliente.query.filter_by(email=CLIENTE).one().id
    assert p["pagamentos"] == []
    assert {(i["sabor"], i["quantidade"], i["preco_unitario"], i["subtotal"]) for i in p["itens"]} == {
        ("Queijo", 1, 5.0, 5.0), ("Queijo com presunto", 2, 7.0, 14.0)}


def test_preco_e_gravado_no_item_e_nao_muda_depois(seeded, client):
    registro = ProdutoUnidade.query.filter_by(id_unidade=unidade("COMPLETA"), id_sabor=sabor("Queijo")).one()
    registro.preco_local = 5.5
    db.session.commit()
    id_pedido = pedir(client, CLIENTE, [item("Queijo", 2)]).get_json()["id"]
    registro.preco_local = 9
    db.session.commit()
    p = client.get(f"{B}/pedidos/{id_pedido}", headers=cabecalho(client, CLIENTE)).get_json()
    assert p["itens"][0]["preco_unitario"] == 5.5 and p["valor_total"] == 11.0


def test_mesmo_sabor_repetido_e_somado(seeded, client):
    p = pedir(client, CLIENTE, [item("Queijo", 1), item("Queijo", 3)]).get_json()
    assert len(p["itens"]) == 1 and p["itens"][0]["quantidade"] == 4 and p["valor_total"] == 20.0


def test_cliente_nao_define_dono_total_nem_status(seeded, client):
    p = pedir(client, CLIENTE, [item("Queijo")], id_cliente=999, valor_total=0.01, id_status=4, status="RETIRADO").get_json()
    assert p["id_cliente"] == Cliente.query.filter_by(email=CLIENTE).one().id
    assert p["valor_total"] == 5.0 and p["status_codigo"] == "AGUARDANDO_PAGAMENTO"


def test_funcionario_registra_venda_de_balcao(seeded, client):
    sem_cadastro = pedir(client, "funcionario", [item("Queijo")], canal="BALCAO")
    assert sem_cadastro.status_code == 201 and sem_cadastro.get_json()["id_cliente"] is None
    cliente = Cliente.query.filter_by(email=CLIENTE).one()
    com_cadastro = pedir(client, "gerente", [item("Queijo")], canal="BALCAO", id_cliente=cliente.id)
    assert com_cadastro.get_json()["id_cliente"] == cliente.id


def test_funcionario_com_cliente_inexistente(seeded, client):
    r = pedir(client, "funcionario", [item("Queijo")], canal="BALCAO", id_cliente=9999)
    assert r.status_code == 404 and r.get_json()["erro"] == "CLIENTE_NAO_ENCONTRADO"


def test_funcionario_nao_vende_em_outra_unidade(seeded, client):
    r = pedir(client, "funcionario", [item("Queijo")], id_unidade=unidade("REDUZIDA"), canal="BALCAO")
    assert r.status_code == 403 and r.get_json()["erro"] == "SEM_PERMISSAO"


def test_cliente_nao_usa_o_canal_balcao(seeded, client):
    r = pedir(client, CLIENTE, [item("Queijo")], canal="BALCAO")
    assert r.status_code == 422 and r.get_json()["erro"] == "CANAL_NAO_PERMITIDO"


@pytest.mark.parametrize("canal", ["APP", "TOTEM", "PICKUP"])
def test_canais_do_cliente(seeded, client, canal):
    r = pedir(client, CLIENTE, [item("Queijo")], canal=canal)
    assert r.status_code == 201 and r.get_json()["canal"] == canal


def test_item_indisponivel_na_unidade_reduzida(seeded, client):
    r = pedir(client, CLIENTE, [item("Queijo"), item("Ovo com queijo")], id_unidade=unidade("REDUZIDA"))
    assert r.status_code == 422
    corpo = r.get_json()
    assert corpo["erro"] == "ITEM_INDISPONIVEL"
    assert corpo["detalhes"] == [{"id_sabor": sabor("Ovo com queijo"), "motivo": "INDISPONIVEL_NA_UNIDADE"}]


def test_sabor_desativado_pelo_gerente_nao_pode_ser_pedido(seeded, client):
    ProdutoUnidade.query.filter_by(id_unidade=unidade("COMPLETA"), id_sabor=sabor("Queijo")).one().esta_disponivel = False
    db.session.commit()
    r = pedir(client, CLIENTE, [item("Queijo")])
    assert r.status_code == 422 and r.get_json()["detalhes"][0]["motivo"] == "INDISPONIVEL_NA_UNIDADE"


def test_sazonalidade_no_pedido(seeded, client, monkeypatch):
    ano = date.today().year
    junino = [item("Bolo de milho (junino)")]
    monkeypatch.setattr("app.utils.tempo.hoje", lambda: date(ano, 11, 10))
    fora = pedir(client, CLIENTE, junino)
    assert fora.status_code == 422 and fora.get_json()["detalhes"][0]["motivo"] == "FORA_DE_ESTACAO"
    monkeypatch.setattr("app.utils.tempo.hoje", lambda: date(ano, 6, 15))
    assert pedir(client, CLIENTE, junino).status_code == 201


def test_todos_os_problemas_sao_listados_de_uma_vez(seeded, client):
    r = pedir(client, CLIENTE, [item("Ovo com queijo"), item("Carne de sol"), {"id_sabor": 9999, "quantidade": 1}],
              id_unidade=unidade("REDUZIDA"))
    motivos = {d["id_sabor"]: d["motivo"] for d in r.get_json()["detalhes"]}
    assert motivos == {sabor("Ovo com queijo"): "INDISPONIVEL_NA_UNIDADE", sabor("Carne de sol"): "INDISPONIVEL_NA_UNIDADE",
                       9999: "SABOR_INEXISTENTE"}


def test_unidade_inexistente(seeded, client):
    r = pedir(client, CLIENTE, [item("Queijo")], id_unidade=9999)
    assert r.status_code == 404 and r.get_json()["erro"] == "UNIDADE_NAO_ENCONTRADA"


@pytest.mark.parametrize("ajuste", [
    {"itens": []},
    {"itens": [{"id_sabor": 1, "quantidade": 0}]},
    {"itens": [{"id_sabor": 1, "quantidade": -2}]},
    {"itens": [{"id_sabor": 1, "quantidade": 51}]},
    {"itens": [{"id_sabor": 1, "quantidade": "2"}]},
    {"itens": [{"id_sabor": 1, "quantidade": 1.5}]},
    {"itens": [{"quantidade": 1}]},
    {"itens": "queijo"},
    {"canal": "CARRIER_PIGEON"},
    {"canal": None},
])
def test_pedido_com_dados_invalidos(seeded, client, ajuste):
    corpo = {"id_unidade": unidade("COMPLETA"), "canal": "APP", "itens": [{"id_sabor": 1, "quantidade": 1}], **ajuste}
    r = client.post(f"{B}/pedidos", json=corpo, headers=cabecalho(client, CLIENTE))
    assert r.status_code == 400 and r.get_json()["erro"] == "DADOS_INVALIDOS"


def test_erro_em_item_aponta_o_campo_exato(seeded, client):
    corpo = {"id_unidade": unidade("COMPLETA"), "canal": "APP", "itens": [{"id_sabor": 1, "quantidade": 1}, {"id_sabor": 1, "quantidade": 0}]}
    r = client.post(f"{B}/pedidos", json=corpo, headers=cabecalho(client, CLIENTE))
    assert {d["campo"] for d in r.get_json()["detalhes"]} == {"itens[1].quantidade"}


def test_campos_obrigatorios_do_pedido(seeded, client):
    r = client.post(f"{B}/pedidos", json={}, headers=cabecalho(client, CLIENTE))
    assert {d["campo"] for d in r.get_json()["detalhes"]} == {"id_unidade", "canal", "itens"}


def test_quantidade_somada_acima_do_limite(seeded, client):
    r = pedir(client, CLIENTE, [item("Queijo", 30), item("Queijo", 30)])
    assert r.status_code == 400 and r.get_json()["erro"] == "QUANTIDADE_INVALIDA"


def test_criar_pedido_exige_login_e_perfil(seeded, client):
    corpo = {"id_unidade": unidade("COMPLETA"), "canal": "APP", "itens": [item("Queijo")]}
    assert client.post(f"{B}/pedidos", json=corpo).status_code == 401
    assert client.post(f"{B}/pedidos", json=corpo, headers=cabecalho(client, "matriz")).status_code == 403


# ---------- consulta ----------
def test_cliente_lista_apenas_os_seus(seeded, client):
    pedido_simples(client)
    outra = cadastrar_cliente(client)
    pedido_simples(client, outra)
    assert client.get(f"{B}/pedidos", headers=cabecalho(client, CLIENTE)).get_json()["total"] == 1
    assert client.get(f"{B}/pedidos", headers=cabecalho(client, outra)).get_json()["total"] == 1


def test_cliente_nao_acessa_pedido_de_outro(seeded, client):
    id_pedido = pedido_simples(client)
    intruso = cabecalho(client, cadastrar_cliente(client))
    for rota in ("", "/status", "/pagamentos"):
        r = client.get(f"{B}/pedidos/{id_pedido}{rota}", headers=intruso)
        assert r.status_code == 403 and r.get_json()["erro"] == "SEM_PERMISSAO"


def test_equipe_so_ve_pedidos_da_propria_unidade(seeded, client):
    id_pedido = pedido_simples(client)  # unidade COMPLETA
    assert client.get(f"{B}/pedidos/{id_pedido}", headers=cabecalho(client, "funcionario")).status_code == 200
    assert client.get(f"{B}/pedidos/{id_pedido}", headers=cabecalho(client, "gerente")).status_code == 200
    de_fora = cabecalho(client, novo_funcionario(unidade("REDUZIDA")))
    assert client.get(f"{B}/pedidos/{id_pedido}", headers=de_fora).status_code == 403
    assert client.get(f"{B}/pedidos", headers=de_fora).get_json()["total"] == 0
    assert client.get(f"{B}/pedidos?id_unidade={unidade('COMPLETA')}", headers=de_fora).status_code == 403


def test_matriz_ve_tudo_e_filtra(seeded, client):
    pedido_simples(client)
    pedir(client, CLIENTE, [item("Queijo")], id_unidade=unidade("REDUZIDA"))
    h = cabecalho(client, "matriz")
    assert client.get(f"{B}/pedidos", headers=h).get_json()["total"] == 2
    assert client.get(f"{B}/pedidos?id_unidade={unidade('REDUZIDA')}", headers=h).get_json()["total"] == 1
    assert client.get(f"{B}/pedidos?status=aguardando_pagamento", headers=h).get_json()["total"] == 2
    assert client.get(f"{B}/pedidos?status=RETIRADO", headers=h).get_json()["total"] == 0


def test_filtro_por_data_e_paginacao(seeded, client):
    pedido_simples(client)
    pedido_simples(client)
    h = cabecalho(client, CLIENTE)
    hoje = date.today().isoformat()
    assert client.get(f"{B}/pedidos?data_inicio={hoje}&data_fim={hoje}", headers=h).get_json()["total"] == 2
    assert client.get(f"{B}/pedidos?data_fim=2000-01-01", headers=h).get_json()["total"] == 0
    assert client.get(f"{B}/pedidos?data_inicio=2999-01-01", headers=h).get_json()["total"] == 0
    pagina = client.get(f"{B}/pedidos?tamanho=1&pagina=2", headers=h).get_json()
    assert len(pagina["itens"]) == 1 and pagina["total"] == 2 and "itens" not in pagina["itens"][0]


@pytest.mark.parametrize("consulta", ["status=VOANDO", "data_inicio=ontem", "id_unidade=abc", "pagina=0", "tamanho=500"])
def test_filtros_invalidos(seeded, client, consulta):
    r = client.get(f"{B}/pedidos?{consulta}", headers=cabecalho(client, "matriz"))
    assert r.status_code == 400 and r.get_json()["erro"] == "PARAMETRO_INVALIDO"


def test_pedido_inexistente_e_sem_token(seeded, client):
    h = cabecalho(client, CLIENTE)
    for rota in ("", "/status", "/pagamentos"):
        assert client.get(f"{B}/pedidos/9999{rota}", headers=h).status_code == 404
    assert client.get(f"{B}/pedidos").status_code == 401
    assert client.get(f"{B}/pedidos/1").status_code == 401


def test_acompanhamento_do_status(seeded, client):
    id_pedido = pedido_simples(client)
    h = cabecalho(client, CLIENTE)
    antes = client.get(f"{B}/pedidos/{id_pedido}/status", headers=h).get_json()
    assert antes["status_codigo"] == "AGUARDANDO_PAGAMENTO" and antes["pagamento"] is None
    pagar(client, id_pedido)
    depois = client.get(f"{B}/pedidos/{id_pedido}/status", headers=h).get_json()
    assert depois["status_codigo"] == "EM_PRODUCAO" and depois["pagamento"]["status_codigo"] == "EFETUADO"


# ---------- status (equipe) ----------
def _status(client, login, id_pedido, status):
    return client.patch(f"{B}/pedidos/{id_pedido}/status", json={"status": status}, headers=cabecalho(client, login))


def test_fluxo_completo_ate_a_retirada(seeded, client):
    id_pedido = pedido_em_producao(client)
    r = _status(client, "funcionario", id_pedido, "PRONTO")
    assert r.status_code == 200 and r.get_json()["status"] == "Pedido pronto, pode retirar"
    r = _status(client, "gerente", id_pedido, "RETIRADO")  # gerente herda o que o funcionário faz
    assert r.status_code == 200 and r.get_json()["status_codigo"] == "RETIRADO"


@pytest.mark.parametrize("alvo", ["PRONTO", "RETIRADO"])
def test_nao_avanca_pedido_que_ainda_nao_foi_pago(seeded, client, alvo):
    id_pedido = pedido_simples(client)
    r = _status(client, "funcionario", id_pedido, alvo)
    assert r.status_code == 409 and r.get_json()["erro"] == "TRANSICAO_INVALIDA"


def test_producao_so_comeca_com_pagamento_confirmado(seeded, client):
    r = _status(client, "funcionario", pedido_simples(client), "EM_PRODUCAO")
    assert r.status_code == 409 and "pagamento" in r.get_json()["mensagem"]


def test_nao_pula_etapas_nem_volta(seeded, client):
    id_pedido = pedido_em_producao(client)
    assert _status(client, "funcionario", id_pedido, "RETIRADO").status_code == 409  # pula PRONTO
    _status(client, "funcionario", id_pedido, "PRONTO")
    assert _status(client, "funcionario", id_pedido, "PRONTO").status_code == 409     # repete
    _status(client, "funcionario", id_pedido, "RETIRADO")
    assert _status(client, "funcionario", id_pedido, "PRONTO").status_code == 409     # volta de um estado final


def test_cancelamento_nao_e_transicao_valida(seeded, client):
    r = _status(client, "funcionario", pedido_em_producao(client), "CANCELADO_EMPRESA")
    assert r.status_code == 409 and r.get_json()["erro"] == "TRANSICAO_INVALIDA"


@pytest.mark.parametrize("corpo", [{}, {"status": "VOANDO"}, {"status": None}])
def test_status_invalido(seeded, client, corpo):
    id_pedido = pedido_em_producao(client)
    r = client.patch(f"{B}/pedidos/{id_pedido}/status", json=corpo, headers=cabecalho(client, "funcionario"))
    assert r.status_code == 400 and r.get_json()["erro"] == "DADOS_INVALIDOS"


def test_quem_pode_avancar_o_status(seeded, client):
    id_pedido = pedido_em_producao(client)
    assert _status(client, CLIENTE, id_pedido, "PRONTO").status_code == 403
    assert _status(client, "matriz", id_pedido, "PRONTO").status_code == 403
    de_fora = novo_funcionario(unidade("REDUZIDA"))
    assert _status(client, de_fora, id_pedido, "PRONTO").status_code == 403
    assert client.patch(f"{B}/pedidos/{id_pedido}/status", json={"status": "PRONTO"}).status_code == 401
    assert _status(client, "funcionario", 9999, "PRONTO").status_code == 404
