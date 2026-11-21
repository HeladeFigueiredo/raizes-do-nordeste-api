"""Paginação padrão das listagens: ?pagina=1&tamanho=20."""
from flask import request

from app.errors import ErroNegocio


def parametros_paginacao(tamanho_padrao: int = 20, tamanho_max: int = 100):
    try:
        pagina = int(request.args.get("pagina", 1))
        tamanho = int(request.args.get("tamanho", tamanho_padrao))
    except ValueError:
        raise ErroNegocio("PARAMETRO_INVALIDO", "'pagina' e 'tamanho' devem ser números inteiros.", 400)
    if pagina < 1 or not 1 <= tamanho <= tamanho_max:
        raise ErroNegocio("PARAMETRO_INVALIDO", f"'pagina' deve ser >= 1 e 'tamanho' entre 1 e {tamanho_max}.", 400)
    return pagina, tamanho


def paginar(consulta, pagina: int, tamanho: int):
    """Devolve (itens, total) de uma consulta SQLAlchemy já ordenada."""
    total = consulta.count()
    itens = consulta.offset((pagina - 1) * tamanho).limit(tamanho).all()
    return itens, total
