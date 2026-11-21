import hmac

from flask import Blueprint, current_app, jsonify, request

from app.errors import ErroNegocio
from app.schemas.pedido import RetornoPagamentoSchema
from app.serializers import pagamento_json, status_pedido_json
from app.services import pagamento_service
from app.validacao import carregar

bp = Blueprint("pagamentos", __name__)


def _exigir_chave_do_gateway() -> None:
    enviada = request.headers.get("X-API-Key", "")
    esperada = current_app.config["GATEWAY_API_KEY"]
    if not enviada or not hmac.compare_digest(enviada.encode(), esperada.encode()):
        raise ErroNegocio("CHAVE_INVALIDA", "Chave de API inválida ou ausente (cabeçalho X-API-Key).", 401)


@bp.post("/pagamentos/retorno")
def retorno_do_gateway():
    """Webhook do gateway: confirma ou nega o pagamento. Autenticado por chave de API, sem JWT.
    Idempotente: o gateway pode reenviar o mesmo resultado sem efeito colateral."""
    _exigir_chave_do_gateway()
    pagamento, pedido, repetido = pagamento_service.registrar_retorno(carregar(RetornoPagamentoSchema()))
    pag, ped = pagamento_json(pagamento), status_pedido_json(pedido.id_status)
    corpo = {
        "id_pedido": pedido.id,
        "status_pagamento": pag["status"], "status_pagamento_codigo": pag["status_codigo"],
        "status_pedido": ped["status"], "status_pedido_codigo": ped["status_codigo"],
        "ja_processado": repetido,
    }
    return jsonify(corpo), 200
