"""Regras de negócio de cadastro e autenticação."""
from sqlalchemy.exc import IntegrityError

from app.constants import PERFIL_CLIENTE
from app.errors import ErroNegocio
from app.extensions import db
from app.models import Cliente, Usuario
from app.models.base import agora
from app.security import gerar_token
from app.utils.cpf import formatar_cpf


def cadastrar_cliente(dados: dict) -> Cliente:
    cpf = formatar_cpf(dados["cpf"])
    email = dados["email"].strip().lower()

    if Cliente.query.filter_by(cpf=cpf).first():
        raise ErroNegocio("CPF_JA_CADASTRADO", "Já existe um cadastro com este CPF.", 409)
    if Cliente.query.filter_by(email=email).first():
        raise ErroNegocio("EMAIL_JA_CADASTRADO", "Já existe um cadastro com este e-mail.", 409)

    cliente = Cliente(
        nome=dados["nome"].strip(), cpf=cpf, email=email,
        data_nascimento=dados["data_nascimento"], cidade=dados.get("cidade"),
        consentimento_lgpd=True, data_consentimento=agora(),
    )
    cliente.definir_senha(dados["senha"])
    db.session.add(cliente)
    try:
        db.session.commit()
    except IntegrityError:  # duas requisições simultâneas com o mesmo CPF ou e-mail
        db.session.rollback()
        raise ErroNegocio("CADASTRO_DUPLICADO", "CPF ou e-mail já cadastrado.", 409)
    return cliente


def autenticar(login: str, senha: str) -> dict:
    """Login do cliente (e-mail) ou da equipe (login). Mesma resposta para qualquer falha."""
    login = login.strip()
    if "@" in login:
        cliente = Cliente.query.filter_by(email=login.lower()).first()
        if cliente and cliente.conferir_senha(senha):
            token = gerar_token(id=cliente.id, tipo="cliente", perfil=PERFIL_CLIENTE)
            return {"token": token, "perfil": PERFIL_CLIENTE}
    else:
        usuario = Usuario.query.filter_by(login=login).first()
        if usuario and usuario.conferir_senha(senha):
            perfil = usuario.perfil.nome
            token = gerar_token(id=usuario.id, tipo="equipe", perfil=perfil, id_unidade=usuario.equipe.id_unidade)
            return {"token": token, "perfil": perfil}
    raise ErroNegocio("CREDENCIAIS_INVALIDAS", "Login ou senha inválidos.", 401)
