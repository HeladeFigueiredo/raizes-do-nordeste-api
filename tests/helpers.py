"""Funções auxiliares compartilhadas pelos testes."""
from app.extensions import db
from app.models import Equipe, Perfil, Sabor, Unidade, Usuario

B = "/api/v1"
CHAVE_GATEWAY = "chave-do-gateway-dev"
CLIENTE = "cliente@exemplo.com"


def cabecalho(client, login, senha="senha123"):
    r = client.post(f"{B}/auth/login", json={"login": login, "senha": senha})
    assert r.status_code == 200, r.get_json()
    return {"Authorization": f"Bearer {r.get_json()['access_token']}"}


def sabor(nome):
    return Sabor.query.filter_by(nome=nome).one().id


def unidade(tipo):
    """'COMPLETA' é a unidade do gerente e do funcionário do seed. 'REDUZIDA' é o quiosque."""
    return Unidade.query.filter_by(tipo_cozinha=tipo).one().id


def item(nome, quantidade=1):
    return {"id_sabor": sabor(nome), "quantidade": quantidade}


def pedir(client, login, itens, id_unidade=None, canal="APP", **extra):
    corpo = {"id_unidade": id_unidade or unidade("COMPLETA"), "canal": canal, "itens": itens, **extra}
    return client.post(f"{B}/pedidos", json=corpo, headers=cabecalho(client, login))


def pedido_simples(client, login=CLIENTE):
    r = pedir(client, login, [item("Queijo"), item("Queijo com presunto", 2)])
    assert r.status_code == 201, r.get_json()
    return r.get_json()["id"]


def solicitar(client, headers, id_pedido):
    return client.post(f"{B}/pedidos/{id_pedido}/pagamentos", headers=headers)


def retorno(client, transacao, resultado, chave=CHAVE_GATEWAY):
    return client.post(f"{B}/pagamentos/retorno", json={"id_transacao_externa": transacao, "resultado": resultado},
                       headers={"X-API-Key": chave})


def pagar(client, id_pedido, login=CLIENTE, resultado="APROVADO"):
    r = solicitar(client, cabecalho(client, login), id_pedido)
    assert r.status_code == 202, r.get_json()
    transacao = r.get_json()["id_transacao_externa"]
    assert retorno(client, transacao, resultado).status_code == 200
    return transacao


def pedido_em_producao(client, login=CLIENTE):
    id_pedido = pedido_simples(client, login)
    pagar(client, id_pedido, login)
    return id_pedido


def novo_funcionario(id_unidade, login="func_quiosque", perfil="FUNCIONARIO"):
    """Cria um membro da equipe com acesso na unidade informada (senha123)."""
    membro = Equipe(nome=f"Equipe {login}", funcao="atendente", cpf=f"999.{abs(hash(login)) % 900 + 100}.000-00", id_unidade=id_unidade)
    db.session.add(membro)
    db.session.flush()
    usuario = Usuario(id_equipe=membro.id, id_perfil=Perfil.query.filter_by(nome=perfil).one().id, login=login)
    usuario.definir_senha("senha123")
    db.session.add(usuario)
    db.session.commit()
    return login


def cadastrar_cliente(client, email="outra@exemplo.com", cpf="935.411.347-80"):
    r = client.post(f"{B}/auth/cadastro", json={
        "nome": "Outra Cliente", "cpf": cpf, "email": email, "senha": "senha123", "data_nascimento": "1990-01-01"})
    assert r.status_code == 201, r.get_json()
    return email
