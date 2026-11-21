from flask import Blueprint, current_app, jsonify

from app.models import Cliente
from app.schemas.auth import CadastroSchema, LoginSchema
from app.services import auth_service
from app.utils.cpf import mascarar_cpf
from app.validacao import carregar

bp = Blueprint("auth", __name__)


def _cliente_json(c: Cliente) -> dict:
    return {
        "id": c.id, "nome": c.nome, "email": c.email, "cpf": mascarar_cpf(c.cpf),
        "data_nascimento": c.data_nascimento.isoformat(), "idade": c.idade,
        "cidade": c.cidade, "consentimento_lgpd": c.consentimento_lgpd,
        "data_consentimento": c.data_consentimento.isoformat() + "Z" if c.data_consentimento else None,
    }


@bp.post("/auth/cadastro")
def cadastro():
    """Cadastra um cliente. O CPF é validado e a senha é guardada apenas como hash."""
    cliente = auth_service.cadastrar_cliente(carregar(CadastroSchema()))
    return jsonify(_cliente_json(cliente)), 201


@bp.post("/auth/login")
def login():
    """Autentica cliente (e-mail) ou equipe (login) e devolve o token JWT."""
    dados = carregar(LoginSchema())
    resultado = auth_service.autenticar(dados["login"], dados["senha"])
    expira = int(current_app.config["JWT_ACCESS_TOKEN_EXPIRES"].total_seconds())
    return jsonify({
        "access_token": resultado["token"], "token_type": "Bearer",
        "expires_in": expira, "perfil": resultado["perfil"],
    }), 200
