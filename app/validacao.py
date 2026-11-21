"""Leitura e validação do corpo JSON das requisições."""
from flask import request

from app.errors import ErroNegocio


def corpo_json() -> dict:
    dados = request.get_json(silent=True)
    if not isinstance(dados, dict):
        raise ErroNegocio("CORPO_INVALIDO", "Envie um corpo JSON válido (objeto).", 400)
    return dados


def carregar(schema, dados: dict | None = None):
    """Valida o corpo com o schema. Em caso de erro, o handler responde 400 com os detalhes."""
    return schema.load(dados if dados is not None else corpo_json())
