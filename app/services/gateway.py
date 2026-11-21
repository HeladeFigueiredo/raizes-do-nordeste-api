"""Integração com o gateway de pagamento (SIMULADA).

O sistema Raízes do Nordeste não processa pagamentos. Ele solicita ao gateway e depois recebe o
resultado em POST /pagamentos/retorno. Para integrar um gateway real, substitua apenas a função
solicitar_pagamento() abaixo; o restante do sistema não muda.
"""
import uuid

from flask import current_app


class GatewayIndisponivel(Exception):
    """O gateway não respondeu ou recusou a solicitação."""


def solicitar_pagamento(id_pedido: int, valor) -> str:
    """Pede a cobrança ao gateway e devolve o id da transação gerado por ele."""
    if not current_app.config.get("GATEWAY_DISPONIVEL", True):
        raise GatewayIndisponivel("Gateway de pagamento indisponível.")
    return "SIM-" + uuid.uuid4().hex[:12].upper()
