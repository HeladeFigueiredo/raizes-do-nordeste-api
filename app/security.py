"""Token JWT, perfis de acesso e escopo por unidade."""
from dataclasses import dataclass
from functools import wraps
from typing import Optional

from flask_jwt_extended import create_access_token, get_jwt, get_jwt_identity, verify_jwt_in_request

from app.constants import PERFIL_FUNCIONARIO, PERFIL_GERENTE, PERFIL_MATRIZ
from app.errors import ErroNegocio, resposta_erro
from app.extensions import jwt

# O gerente herda tudo o que o funcionário pode fazer. A matriz é um perfil à parte (gestão e relatórios).
HERANCA_PERFIS = {PERFIL_GERENTE: {PERFIL_GERENTE, PERFIL_FUNCIONARIO}}


def gerar_token(*, id: int, tipo: str, perfil: str, id_unidade: Optional[int] = None) -> str:
    claims = {"tipo": tipo, "perfil": perfil, "id_unidade": id_unidade}
    return create_access_token(identity=str(id), additional_claims=claims)


@dataclass(frozen=True)
class UsuarioAtual:
    id: int
    tipo: str  # "cliente" ou "equipe"
    perfil: str
    id_unidade: Optional[int]

    @property
    def e_cliente(self) -> bool:
        return self.tipo == "cliente"

    def pode_acessar_unidade(self, id_unidade: int) -> bool:
        """Matriz acessa qualquer unidade. Funcionário e gerente, apenas a própria."""
        if self.perfil == PERFIL_MATRIZ:
            return True
        return self.tipo == "equipe" and self.id_unidade == id_unidade


def usuario_atual() -> UsuarioAtual:
    claims = get_jwt()
    return UsuarioAtual(
        id=int(get_jwt_identity()), tipo=claims.get("tipo"),
        perfil=claims.get("perfil"), id_unidade=claims.get("id_unidade"),
    )


def autenticado(fn):
    """Exige um token válido, de qualquer perfil."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        return fn(*args, **kwargs)
    return wrapper


def perfis_permitidos(*permitidos: str):
    """Exige token válido e um dos perfis informados (considerando a herança do gerente)."""
    def decorador(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            usuario = usuario_atual()
            efetivos = HERANCA_PERFIS.get(usuario.perfil, {usuario.perfil})
            if not efetivos & set(permitidos):
                raise ErroNegocio("SEM_PERMISSAO", "Seu perfil não tem permissão para esta operação.", 403)
            return fn(*args, **kwargs)
        return wrapper
    return decorador


def exigir_unidade(id_unidade: int) -> None:
    """Bloqueia (403) quem tenta acessar dados de outra unidade."""
    if not usuario_atual().pode_acessar_unidade(id_unidade):
        raise ErroNegocio("SEM_PERMISSAO", "Você só pode acessar dados da sua própria unidade.", 403)


def registrar_respostas_jwt():
    """Erros do JWT no mesmo padrão JSON do restante da API."""
    @jwt.unauthorized_loader
    def _sem_token(motivo):
        return resposta_erro("NAO_AUTENTICADO", "Envie o token no cabeçalho Authorization: Bearer <token>.", 401)

    @jwt.invalid_token_loader
    def _token_invalido(motivo):
        return resposta_erro("TOKEN_INVALIDO", "Token inválido.", 401)

    @jwt.expired_token_loader
    def _token_expirado(cabecalho, dados):
        return resposta_erro("TOKEN_EXPIRADO", "Token expirado. Faça login novamente.", 401)
