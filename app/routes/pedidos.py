from datetime import date

from flask import Blueprint, jsonify, request

from app.constants import PERFIL_CLIENTE, PERFIL_FUNCIONARIO, StatusPedidoId
from app.errors import ErroNegocio
from app.schemas.pedido import PedidoSchema, StatusSchema
from app.security import autenticado, perfis_permitidos, usuario_atual
from app.serializers import pagamento_json, pedido_json, status_pedido_json
from app.services import pagamento_service, pedido_service as servico
from app.utils.paginacao import paginar, parametros_paginacao
from app.validacao import carregar

bp = Blueprint("pedidos", __name__)


def _data(nome: str):
    texto = request.args.get(nome)
    if not texto:
        return None
    try:
        return date.fromisoformat(texto)
    except ValueError:
        raise ErroNegocio("PARAMETRO_INVALIDO", f"Use o formato AAAA-MM-DD em '{nome}'.", 400)


def _inteiro(nome: str):
    texto = request.args.get(nome)
    if texto is None:
        return None
    try:
        return int(texto)
    except ValueError:
        raise ErroNegocio("PARAMETRO_INVALIDO", f"'{nome}' deve ser um número inteiro.", 400)


@bp.post("/pedidos")
@perfis_permitidos(PERFIL_CLIENTE, PERFIL_FUNCIONARIO)  # o gerente herda o perfil de funcionário
def criar_pedido():
    """Cria o pedido. Valida disponibilidade na unidade e na época, grava o preço do momento e calcula o total."""
    pedido = servico.criar_pedido(usuario_atual(), carregar(PedidoSchema()))
    return jsonify(pedido_json(pedido)), 201


@bp.get("/pedidos")
@autenticado
def listar_pedidos():
    """Lista pedidos (mais recentes primeiro). Filtros: id_unidade, status, data_inicio, data_fim. Cliente vê só os seus."""
    pagina, tamanho = parametros_paginacao()
    status = request.args.get("status")
    if status:
        status = status.upper()
        if status not in StatusPedidoId.__members__:
            raise ErroNegocio("PARAMETRO_INVALIDO", "Status inválido. Valores: " + ", ".join(StatusPedidoId.__members__), 400)
    consulta = servico.listar_pedidos(usuario_atual(), _inteiro("id_unidade"), status, _data("data_inicio"), _data("data_fim"))
    pedidos, total = paginar(consulta, pagina, tamanho)
    return jsonify({"itens": [pedido_json(p, detalhado=False) for p in pedidos], "pagina": pagina, "tamanho": tamanho, "total": total})


@bp.get("/pedidos/<int:id_pedido>")
@autenticado
def obter_pedido(id_pedido):
    pedido = servico.obter_pedido(id_pedido)
    servico.exigir_acesso(usuario_atual(), pedido)
    return jsonify(pedido_json(pedido))


@bp.get("/pedidos/<int:id_pedido>/status")
@autenticado
def status_do_pedido(id_pedido):
    """Consulta leve usada no acompanhamento pelo app."""
    pedido = servico.obter_pedido(id_pedido)
    servico.exigir_acesso(usuario_atual(), pedido)
    ultimo = max(pedido.pagamentos, key=lambda p: p.id, default=None)
    return jsonify({
        "id": pedido.id, **status_pedido_json(pedido.id_status),
        "pagamento": pagamento_json(ultimo) if ultimo else None,
    })


@bp.patch("/pedidos/<int:id_pedido>/status")
@perfis_permitidos(PERFIL_FUNCIONARIO)
def avancar_status(id_pedido):
    """Equipe avança o pedido: EM_PRODUCAO -> PRONTO -> RETIRADO. Outras transições respondem 409."""
    dados = carregar(StatusSchema())
    pedido = servico.avancar_status(usuario_atual(), id_pedido, dados["status"])
    return jsonify({"id": pedido.id, **status_pedido_json(pedido.id_status)})


@bp.post("/pedidos/<int:id_pedido>/pagamentos")
@perfis_permitidos(PERFIL_CLIENTE, PERFIL_FUNCIONARIO)
def solicitar_pagamento(id_pedido):
    """Solicita o pagamento ao gateway. O resultado chega depois em POST /pagamentos/retorno."""
    pagamento = pagamento_service.solicitar_pagamento(usuario_atual(), id_pedido)
    return jsonify(pagamento_json(pagamento)), 202


@bp.get("/pedidos/<int:id_pedido>/pagamentos")
@autenticado
def listar_pagamentos(id_pedido):
    pagamentos = pagamento_service.listar_pagamentos(usuario_atual(), id_pedido)
    return jsonify({"itens": [pagamento_json(p) for p in pagamentos]})
