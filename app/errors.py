"""Padrão único de erro da API: {"erro": "CODIGO", "mensagem": "texto", "detalhes": [...]}."""
from flask import jsonify
from marshmallow import ValidationError
from werkzeug.exceptions import HTTPException


class ErroNegocio(Exception):
    """Erro de regra de negócio. Os serviços lançam, e o handler converte em resposta JSON."""

    def __init__(self, codigo: str, mensagem: str, status: int = 422, detalhes=None):
        super().__init__(mensagem)
        self.codigo = codigo
        self.mensagem = mensagem
        self.status = status
        self.detalhes = detalhes or []


def resposta_erro(codigo: str, mensagem: str, status: int, detalhes=None):
    corpo = {"erro": codigo, "mensagem": mensagem}
    if detalhes:
        corpo["detalhes"] = detalhes
    return jsonify(corpo), status


def _achatar(mensagens, prefixo=""):
    """Transforma os erros do Marshmallow (inclusive de listas aninhadas) em [{campo, mensagem}]."""
    detalhes = []
    for chave, valor in mensagens.items():
        nome = "corpo" if chave == "_schema" else str(chave)
        if prefixo:
            nome = f"{prefixo}[{nome}]" if isinstance(chave, int) else f"{prefixo}.{nome}"
        if isinstance(valor, dict):
            detalhes.extend(_achatar(valor, nome))
        else:
            for erro in (valor if isinstance(valor, list) else [valor]):
                detalhes.append({"campo": nome, "mensagem": str(erro)})
    return detalhes


def registrar_erros(app):
    @app.errorhandler(ErroNegocio)
    def _negocio(e):
        return resposta_erro(e.codigo, e.mensagem, e.status, e.detalhes)

    @app.errorhandler(ValidationError)
    def _validacao(e):
        detalhes = _achatar(e.messages if isinstance(e.messages, dict) else {"corpo": e.messages})
        return resposta_erro("DADOS_INVALIDOS", "Há campos inválidos na requisição.", 400, detalhes)

    @app.errorhandler(HTTPException)
    def _http(e):
        codigos = {
            400: "REQUISICAO_INVALIDA", 401: "NAO_AUTENTICADO", 403: "SEM_PERMISSAO",
            404: "NAO_ENCONTRADO", 405: "METODO_NAO_PERMITIDO", 409: "CONFLITO",
        }
        mensagens = {
            400: "Requisição inválida.", 401: "Autenticação necessária.", 403: "Você não tem permissão para esta operação.",
            404: "Recurso não encontrado.", 405: "Método não permitido para esta rota.", 409: "Conflito com o estado atual do recurso.",
        }
        return resposta_erro(codigos.get(e.code, "ERRO_HTTP"), mensagens.get(e.code, e.description), e.code)

    @app.errorhandler(Exception)
    def _inesperado(e):
        app.logger.exception("Erro inesperado")
        return resposta_erro("ERRO_INTERNO", "Erro interno do servidor.", 500)
