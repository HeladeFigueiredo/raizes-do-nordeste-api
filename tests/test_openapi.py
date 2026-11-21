import re

from app.openapi import construir_spec
from tests.helpers import B, CLIENTE, cabecalho, item, pagar, pedir, pedido_simples, solicitar

METODOS = {"get", "post", "put", "patch", "delete"}


def _rotas_reais(app):
    reais = set()
    for regra in app.url_map.iter_rules():
        if not regra.rule.startswith("/api/v1"):
            continue
        caminho = re.sub(r"<(?:\w+:)?(\w+)>", r"{\1}", regra.rule[len("/api/v1"):])
        for metodo in regra.methods - {"HEAD", "OPTIONS"}:
            reais.add((metodo.lower(), caminho))
    return reais


def _rotas_documentadas():
    return {(m, c) for c, ops in construir_spec()["paths"].items() for m in ops if m in METODOS}


def test_toda_rota_da_api_esta_documentada_e_vice_versa(app):
    assert _rotas_reais(app) == _rotas_documentadas()


def test_swagger_ui_e_json_sao_servidos(client):
    pagina = client.get("/docs")
    assert pagina.status_code == 200 and b"swagger-ui" in pagina.data
    spec = client.get("/openapi.json").get_json()
    assert spec["openapi"].startswith("3.") and len(spec["paths"]) >= 10


def test_toda_operacao_documenta_exemplos_e_codigos_de_status():
    for caminho, ops in construir_spec()["paths"].items():
        for metodo, op in ops.items():
            assert op["responses"], (metodo, caminho)
            assert any(c.startswith("2") for c in op["responses"]), (metodo, caminho)
            if "requestBody" in op:
                assert "example" in op["requestBody"]["content"]["application/json"], (metodo, caminho)


def _exemplo(caminho, metodo, status):
    corpo = construir_spec()["paths"][caminho][metodo]["responses"][status]["content"]["application/json"]
    return corpo["example"]


def test_exemplos_da_documentacao_tem_os_mesmos_campos_das_respostas_reais(seeded, client):
    login = client.post(f"{B}/auth/login", json={"login": CLIENTE, "senha": "senha123"}).get_json()
    assert set(login) == set(_exemplo("/auth/login", "post", "200"))

    id_pedido = pedido_simples(client)
    h = cabecalho(client, CLIENTE)
    pedido = client.get(f"{B}/pedidos/{id_pedido}", headers=h).get_json()
    assert set(pedido) == set(_exemplo("/pedidos/{id_pedido}", "get", "200"))

    pagamento = solicitar(client, h, id_pedido).get_json()
    assert set(pagamento) == set(_exemplo("/pedidos/{id_pedido}/pagamentos", "post", "202"))

    r = client.post(f"{B}/pagamentos/retorno", headers={"X-API-Key": "chave-do-gateway-dev"},
                    json={"id_transacao_externa": pagamento["id_transacao_externa"], "resultado": "APROVADO"})
    assert set(r.get_json()) == set(_exemplo("/pagamentos/retorno", "post", "200"))

    reg = client.get(f"{B}/auditoria", headers=cabecalho(client, "matriz")).get_json()["itens"][0]
    assert set(reg) == set(_exemplo("/auditoria", "get", "200")["itens"][0])

    erro = pedir(client, CLIENTE, [item("Queijo", 0)]).get_json()
    assert set(erro) <= {"erro", "mensagem", "detalhes"}
