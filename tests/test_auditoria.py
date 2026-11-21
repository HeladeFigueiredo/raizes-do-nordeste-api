import pytest

from tests.helpers import B, CLIENTE, cabecalho, item, pedido_em_producao, pedido_simples, pedir, unidade


def _registros(client, login, consulta=""):
    r = client.get(f"{B}/auditoria{consulta}", headers=cabecalho(client, login))
    assert r.status_code == 200
    return r.get_json()


def test_criar_pedido_gera_registro_de_auditoria(seeded, client):
    id_pedido = pedido_simples(client)
    itens = _registros(client, "matriz", f"?id_pedido={id_pedido}")["itens"]
    assert [i["acao"] for i in itens] == ["PEDIDO_CRIADO"]
    assert itens[0]["tipo_ator"] == "CLIENTE" and "canalPedido=APP" in itens[0]["detalhe"]


def test_fluxo_completo_fica_registrado_em_ordem(seeded, client):
    id_pedido = pedido_em_producao(client)
    for novo in ("PRONTO", "RETIRADO"):
        r = client.patch(f"{B}/pedidos/{id_pedido}/status", json={"status": novo}, headers=cabecalho(client, "funcionario"))
        assert r.status_code == 200
    itens = _registros(client, "matriz", f"?id_pedido={id_pedido}")["itens"]
    assert [i["acao"] for i in reversed(itens)] == [
        "PEDIDO_CRIADO", "PAGAMENTO_SOLICITADO", "PAGAMENTO_RETORNO", "STATUS_ALTERADO", "STATUS_ALTERADO",
    ]
    mudancas = [i for i in itens if i["acao"] == "STATUS_ALTERADO"]
    assert {m["detalhe"] for m in mudancas} == {"EM_PRODUCAO -> PRONTO", "PRONTO -> RETIRADO"}
    assert all(m["tipo_ator"] == "EQUIPE" for m in mudancas)
    retorno_gateway = next(i for i in itens if i["acao"] == "PAGAMENTO_RETORNO")
    assert retorno_gateway["tipo_ator"] == "GATEWAY" and retorno_gateway["id_ator"] is None


def test_transicao_recusada_nao_gera_registro(seeded, client):
    id_pedido = pedido_simples(client)
    r = client.patch(f"{B}/pedidos/{id_pedido}/status", json={"status": "PRONTO"}, headers=cabecalho(client, "funcionario"))
    assert r.status_code == 409
    acoes = [i["acao"] for i in _registros(client, "matriz", f"?id_pedido={id_pedido}")["itens"]]
    assert acoes == ["PEDIDO_CRIADO"]


def test_filtro_por_acao(seeded, client):
    pedido_em_producao(client)
    pedido_simples(client)
    total = _registros(client, "matriz", "?acao=pedido_criado")["total"]
    assert total == 2
    assert _registros(client, "matriz", "?acao=STATUS_ALTERADO")["total"] == 0


def test_gerente_ve_so_a_propria_unidade(seeded, client):
    pedido_simples(client)
    pedir(client, CLIENTE, [item("Queijo")], id_unidade=unidade("REDUZIDA"))
    assert _registros(client, "matriz")["total"] == 2
    assert _registros(client, "gerente")["total"] == 1


@pytest.mark.parametrize("login", [CLIENTE, "funcionario"])
def test_sem_permissao_para_consultar_auditoria(seeded, client, login):
    r = client.get(f"{B}/auditoria", headers=cabecalho(client, login))
    assert r.status_code == 403 and r.get_json()["erro"] == "SEM_PERMISSAO"


def test_auditoria_exige_login_e_valida_parametro(seeded, client):
    assert client.get(f"{B}/auditoria").status_code == 401
    r = client.get(f"{B}/auditoria?id_pedido=abc", headers=cabecalho(client, "matriz"))
    assert r.status_code == 400 and r.get_json()["erro"] == "PARAMETRO_INVALIDO"
