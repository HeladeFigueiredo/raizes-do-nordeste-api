import pytest

from app.models import Pagamento
from tests.helpers import (
    B, CHAVE_GATEWAY, CLIENTE, cabecalho, cadastrar_cliente, novo_funcionario, pagar, pedido_simples, retorno, solicitar,
    unidade,
)


def _pedido(client, id_pedido, login=CLIENTE):
    return client.get(f"{B}/pedidos/{id_pedido}", headers=cabecalho(client, login)).get_json()


# ---------- solicitação ----------
def test_solicitar_pagamento_devolve_202_e_registra(seeded, client):
    id_pedido = pedido_simples(client)
    r = solicitar(client, cabecalho(client, CLIENTE), id_pedido)
    assert r.status_code == 202
    p = r.get_json()
    assert p["status_codigo"] == "PROCESSANDO" and p["valor"] == 19.0 and p["id_transacao_externa"].startswith("SIM-")
    assert _pedido(client, id_pedido)["status_codigo"] == "AGUARDANDO_PAGAMENTO"  # ainda não foi confirmado


def test_funcionario_tambem_solicita_pagamento_do_balcao(seeded, client):
    id_pedido = pedido_simples(client)
    assert solicitar(client, cabecalho(client, "funcionario"), id_pedido).status_code == 202


def test_nao_solicita_duas_vezes_enquanto_processa(seeded, client):
    id_pedido = pedido_simples(client)
    h = cabecalho(client, CLIENTE)
    solicitar(client, h, id_pedido)
    r = solicitar(client, h, id_pedido)
    assert r.status_code == 409 and r.get_json()["erro"] == "PAGAMENTO_EM_ANDAMENTO"
    assert Pagamento.query.count() == 1


def test_nao_solicita_pagamento_de_pedido_ja_pago(seeded, client):
    id_pedido = pedido_simples(client)
    pagar(client, id_pedido)
    r = solicitar(client, cabecalho(client, CLIENTE), id_pedido)
    assert r.status_code == 409 and r.get_json()["erro"] == "PEDIDO_NAO_AGUARDA_PAGAMENTO"


def test_quem_pode_solicitar_pagamento(seeded, client):
    id_pedido = pedido_simples(client)
    assert solicitar(client, cabecalho(client, cadastrar_cliente(client)), id_pedido).status_code == 403
    assert solicitar(client, cabecalho(client, novo_funcionario(unidade("REDUZIDA"))), id_pedido).status_code == 403
    assert solicitar(client, cabecalho(client, "matriz"), id_pedido).status_code == 403
    assert client.post(f"{B}/pedidos/{id_pedido}/pagamentos").status_code == 401
    assert solicitar(client, cabecalho(client, CLIENTE), 9999).status_code == 404


# ---------- retorno do gateway ----------
def test_pagamento_aprovado_coloca_o_pedido_em_producao(seeded, client):
    id_pedido = pedido_simples(client)
    transacao = solicitar(client, cabecalho(client, CLIENTE), id_pedido).get_json()["id_transacao_externa"]
    r = retorno(client, transacao, "APROVADO")
    assert r.status_code == 200
    assert r.get_json() == {
        "id_pedido": id_pedido, "status_pagamento": "Pagamento efetuado", "status_pagamento_codigo": "EFETUADO",
        "status_pedido": "Em produção", "status_pedido_codigo": "EM_PRODUCAO", "ja_processado": False}
    p = _pedido(client, id_pedido)
    assert p["status_codigo"] == "EM_PRODUCAO" and p["pagamentos"][0]["data_retorno"].endswith("Z")


def test_retorno_repetido_e_idempotente(seeded, client):
    id_pedido = pedido_simples(client)
    transacao = solicitar(client, cabecalho(client, CLIENTE), id_pedido).get_json()["id_transacao_externa"]
    retorno(client, transacao, "APROVADO")
    r = retorno(client, transacao, "APROVADO")
    assert r.status_code == 200 and r.get_json()["ja_processado"] is True
    assert _pedido(client, id_pedido)["status_codigo"] == "EM_PRODUCAO"


def test_retorno_com_resultado_diferente_do_ja_registrado(seeded, client):
    id_pedido = pedido_simples(client)
    transacao = solicitar(client, cabecalho(client, CLIENTE), id_pedido).get_json()["id_transacao_externa"]
    retorno(client, transacao, "APROVADO")
    r = retorno(client, transacao, "NEGADO")
    assert r.status_code == 409 and r.get_json()["erro"] == "RETORNO_CONFLITANTE"
    assert _pedido(client, id_pedido)["pagamentos"][0]["status_codigo"] == "EFETUADO"


def test_pagamento_negado_mantem_o_pedido_e_permite_nova_tentativa(seeded, client):
    id_pedido = pedido_simples(client)
    h = cabecalho(client, CLIENTE)
    transacao = solicitar(client, h, id_pedido).get_json()["id_transacao_externa"]
    r = retorno(client, transacao, "NEGADO")
    assert r.get_json()["status_pagamento_codigo"] == "NAO_APROVADO" and r.get_json()["status_pedido_codigo"] == "AGUARDANDO_PAGAMENTO"
    segunda = solicitar(client, h, id_pedido)
    assert segunda.status_code == 202 and segunda.get_json()["id_transacao_externa"] != transacao
    retorno(client, segunda.get_json()["id_transacao_externa"], "APROVADO")
    p = _pedido(client, id_pedido)
    assert p["status_codigo"] == "EM_PRODUCAO"
    assert [x["status_codigo"] for x in p["pagamentos"]] == ["NAO_APROVADO", "EFETUADO"]


def test_erro_no_pagamento_tambem_permite_nova_tentativa(seeded, client):
    id_pedido = pedido_simples(client)
    h = cabecalho(client, CLIENTE)
    transacao = solicitar(client, h, id_pedido).get_json()["id_transacao_externa"]
    assert retorno(client, transacao, "ERRO").get_json()["status_pagamento_codigo"] == "ERRO"
    assert solicitar(client, h, id_pedido).status_code == 202


@pytest.mark.parametrize("chave", [None, "", "chave-errada", "CHAVE-DO-GATEWAY-DEV"])
def test_retorno_exige_a_chave_do_gateway(seeded, client, chave):
    id_pedido = pedido_simples(client)
    transacao = solicitar(client, cabecalho(client, CLIENTE), id_pedido).get_json()["id_transacao_externa"]
    cabecalhos = {"X-API-Key": chave} if chave is not None else {}
    r = client.post(f"{B}/pagamentos/retorno", json={"id_transacao_externa": transacao, "resultado": "APROVADO"}, headers=cabecalhos)
    assert r.status_code == 401 and r.get_json()["erro"] == "CHAVE_INVALIDA"
    assert _pedido(client, id_pedido)["status_codigo"] == "AGUARDANDO_PAGAMENTO"


def test_token_de_usuario_nao_substitui_a_chave_do_gateway(seeded, client):
    r = client.post(f"{B}/pagamentos/retorno", json={"id_transacao_externa": "x", "resultado": "APROVADO"},
                    headers=cabecalho(client, "matriz"))
    assert r.status_code == 401


def test_retorno_de_transacao_desconhecida_e_dados_invalidos(seeded, client):
    assert retorno(client, "SIM-NAO-EXISTE", "APROVADO").status_code == 404
    for corpo in ({}, {"id_transacao_externa": "SIM-1"}, {"id_transacao_externa": "SIM-1", "resultado": "TALVEZ"}):
        r = client.post(f"{B}/pagamentos/retorno", json=corpo, headers={"X-API-Key": CHAVE_GATEWAY})
        assert r.status_code == 400 and r.get_json()["erro"] == "DADOS_INVALIDOS"


# ---------- gateway fora do ar ----------
def test_gateway_indisponivel_responde_502_registra_erro_e_permite_tentar_de_novo(seeded, client):
    id_pedido = pedido_simples(client)
    h = cabecalho(client, CLIENTE)
    seeded.config["GATEWAY_DISPONIVEL"] = False
    r = solicitar(client, h, id_pedido)
    assert r.status_code == 502 and r.get_json()["erro"] == "GATEWAY_INDISPONIVEL"
    pagamentos = _pedido(client, id_pedido)["pagamentos"]
    assert len(pagamentos) == 1 and pagamentos[0]["status_codigo"] == "ERRO" and pagamentos[0]["id_transacao_externa"] is None
    seeded.config["GATEWAY_DISPONIVEL"] = True
    assert solicitar(client, h, id_pedido).status_code == 202


# ---------- consulta ----------
def test_listar_pagamentos_do_pedido_com_escopo(seeded, client):
    id_pedido = pedido_simples(client)
    pagar(client, id_pedido, resultado="NEGADO")
    pagar(client, id_pedido)
    itens = client.get(f"{B}/pedidos/{id_pedido}/pagamentos", headers=cabecalho(client, CLIENTE)).get_json()["itens"]
    assert [i["status_codigo"] for i in itens] == ["NAO_APROVADO", "EFETUADO"]
    assert client.get(f"{B}/pedidos/{id_pedido}/pagamentos", headers=cabecalho(client, "gerente")).status_code == 200
    assert client.get(f"{B}/pedidos/{id_pedido}/pagamentos", headers=cabecalho(client, "matriz")).status_code == 200
    de_fora = cabecalho(client, novo_funcionario(unidade("REDUZIDA")))
    assert client.get(f"{B}/pedidos/{id_pedido}/pagamentos", headers=de_fora).status_code == 403
