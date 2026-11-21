from datetime import timedelta

from flask_jwt_extended import create_access_token

from app.models import Cliente
from app.utils.cpf import cpf_valido, formatar_cpf, mascarar_cpf

CADASTRO_VALIDO = {
    "nome": "Maria da Silva", "cpf": "529.982.247-25", "email": "Maria@Exemplo.com",
    "senha": "senhaforte1", "data_nascimento": "1998-03-10", "cidade": "Olinda",
}


def _login(client, login, senha="senha123"):
    return client.post("/api/v1/auth/login", json={"login": login, "senha": senha})


def _cabecalho(client, login, senha="senha123"):
    token = _login(client, login, senha).get_json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ---------- CPF ----------
def test_cpf_utilitarios():
    assert cpf_valido("529.982.247-25")
    assert cpf_valido("52998224725")
    assert not cpf_valido("111.111.111-11")
    assert not cpf_valido("529.982.247-26")
    assert not cpf_valido("123")
    assert formatar_cpf("52998224725") == "529.982.247-25"
    assert mascarar_cpf("529.982.247-25") == "***.***.***-25"


# ---------- Cadastro ----------
def test_cadastro_ok_sem_expor_senha_e_com_cpf_mascarado(client):
    r = client.post("/api/v1/auth/cadastro", json=CADASTRO_VALIDO)
    assert r.status_code == 201
    corpo = r.get_json()
    assert corpo["email"] == "maria@exemplo.com"  # e-mail normalizado
    assert corpo["cpf"] == "***.***.***-25"
    assert corpo["idade"] >= 0
    assert "senha" not in corpo and "senha_hash" not in corpo
    cliente = Cliente.query.one()
    assert cliente.senha_hash != "senhaforte1"
    assert cliente.cpf == "529.982.247-25"


def test_cadastro_campos_obrigatorios(client):
    r = client.post("/api/v1/auth/cadastro", json={})
    assert r.status_code == 400
    corpo = r.get_json()
    assert corpo["erro"] == "DADOS_INVALIDOS"
    campos = {d["campo"] for d in corpo["detalhes"]}
    assert {"nome", "cpf", "email", "senha", "data_nascimento"} <= campos


def test_cadastro_cpf_invalido(client):
    r = client.post("/api/v1/auth/cadastro", json={**CADASTRO_VALIDO, "cpf": "111.111.111-11"})
    assert r.status_code == 400
    assert any(d["campo"] == "cpf" and d["mensagem"] == "CPF inválido." for d in r.get_json()["detalhes"])


def test_cadastro_senha_curta_email_invalido_e_data_futura(client):
    dados = {**CADASTRO_VALIDO, "senha": "123", "email": "nao-e-email", "data_nascimento": "2999-01-01"}
    r = client.post("/api/v1/auth/cadastro", json=dados)
    assert r.status_code == 400
    campos = {d["campo"] for d in r.get_json()["detalhes"]}
    assert {"senha", "email", "data_nascimento"} <= campos


def test_cadastro_data_em_formato_errado(client):
    r = client.post("/api/v1/auth/cadastro", json={**CADASTRO_VALIDO, "data_nascimento": "10/03/1998"})
    assert r.status_code == 400


def test_cadastro_corpo_que_nao_e_json(client):
    r = client.post("/api/v1/auth/cadastro", data="texto solto", content_type="text/plain")
    assert r.status_code == 400
    assert r.get_json()["erro"] == "CORPO_INVALIDO"


def test_cadastro_cpf_duplicado(client):
    client.post("/api/v1/auth/cadastro", json=CADASTRO_VALIDO)
    r = client.post("/api/v1/auth/cadastro", json={**CADASTRO_VALIDO, "email": "outro@exemplo.com", "cpf": "52998224725"})
    assert r.status_code == 409
    assert r.get_json()["erro"] == "CPF_JA_CADASTRADO"


def test_cadastro_email_duplicado_ignora_maiusculas(client):
    client.post("/api/v1/auth/cadastro", json=CADASTRO_VALIDO)
    r = client.post("/api/v1/auth/cadastro", json={**CADASTRO_VALIDO, "cpf": "935.411.347-80", "email": "MARIA@exemplo.COM"})
    assert r.status_code == 409
    assert r.get_json()["erro"] == "EMAIL_JA_CADASTRADO"


def test_cadastro_ignora_campos_desconhecidos(client):
    r = client.post("/api/v1/auth/cadastro", json={**CADASTRO_VALIDO, "id": 77, "senha_hash": "invasor"})
    assert r.status_code == 201
    cliente = Cliente.query.one()
    assert cliente.id != 77 and cliente.senha_hash != "invasor"  # só os campos conhecidos são usados


# ---------- Login ----------
def test_login_cliente_apos_cadastro(client):
    client.post("/api/v1/auth/cadastro", json=CADASTRO_VALIDO)
    r = _login(client, "maria@exemplo.com", "senhaforte1")
    assert r.status_code == 200
    corpo = r.get_json()
    assert corpo["token_type"] == "Bearer" and corpo["perfil"] == "CLIENTE"
    assert corpo["expires_in"] == 3600 and corpo["access_token"]


def test_login_cliente_com_email_em_maiusculas(seeded, client):
    assert _login(client, "CLIENTE@exemplo.com").status_code == 200


def test_login_equipe_por_perfil(seeded, client):
    for login, perfil in (("funcionario", "FUNCIONARIO"), ("gerente", "GERENTE"), ("matriz", "MATRIZ")):
        r = _login(client, login)
        assert r.status_code == 200
        assert r.get_json()["perfil"] == perfil


def test_login_senha_errada_e_usuario_inexistente_tem_a_mesma_resposta(seeded, client):
    errada = _login(client, "gerente", "errada")
    inexistente = _login(client, "ninguem", "senha123")
    assert errada.status_code == inexistente.status_code == 401
    assert errada.get_json() == inexistente.get_json()
    assert errada.get_json()["erro"] == "CREDENCIAIS_INVALIDAS"
    assert _login(client, "naoexiste@x.com").status_code == 401


def test_login_sem_campos(client):
    r = client.post("/api/v1/auth/login", json={"login": "gerente"})
    assert r.status_code == 400
    assert r.get_json()["erro"] == "DADOS_INVALIDOS"


def test_login_nao_aceita_get(client):
    assert client.get("/api/v1/auth/login").status_code == 405


# ---------- token em rota protegida (GET /pedidos) ----------
def test_rota_protegida_sem_token(client):
    r = client.get("/api/v1/pedidos")
    assert r.status_code == 401
    assert r.get_json()["erro"] == "NAO_AUTENTICADO"


def test_token_invalido(client):
    r = client.get("/api/v1/pedidos", headers={"Authorization": "Bearer abc.def.ghi"})
    assert r.status_code == 401
    assert r.get_json()["erro"] == "TOKEN_INVALIDO"


def test_token_expirado(seeded, client):
    with seeded.app_context():
        token = create_access_token(identity="1", additional_claims={"tipo": "equipe", "perfil": "GERENTE"},
                                    expires_delta=timedelta(seconds=-1))
    r = client.get("/api/v1/pedidos", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401
    assert r.get_json()["erro"] == "TOKEN_EXPIRADO"
