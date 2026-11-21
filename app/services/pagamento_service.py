"""Pagamento desacoplado: solicita ao gateway, registra o resultado e atualiza o status do pedido."""
from app.constants import StatusPagamentoId, StatusPedidoId
from app.errors import ErroNegocio
from app.extensions import db
from app.models import Pagamento
from app.security import UsuarioAtual
from app.services import auditoria_service, gateway
from app.services.pedido_service import (
    PAGAMENTO_EM_ANDAMENTO, exigir_acesso, obter_pedido, tem_pagamento_em_andamento,
)
from app.utils import tempo

_RESULTADO_PARA_STATUS = {
    "APROVADO": StatusPagamentoId.EFETUADO,
    "NEGADO": StatusPagamentoId.NAO_APROVADO,
    "ERRO": StatusPagamentoId.ERRO,
}


def solicitar_pagamento(usuario: UsuarioAtual, id_pedido: int) -> Pagamento:
    pedido = obter_pedido(id_pedido)
    exigir_acesso(usuario, pedido)

    if pedido.id_status != int(StatusPedidoId.AGUARDANDO_PAGAMENTO):
        raise ErroNegocio("PEDIDO_NAO_AGUARDA_PAGAMENTO", "Este pedido não está aguardando pagamento.", 409)
    if tem_pagamento_em_andamento(pedido):
        raise ErroNegocio("PAGAMENTO_EM_ANDAMENTO", "Já existe um pagamento em andamento para este pedido.", 409)

    pagamento = Pagamento(id_pedido=pedido.id, id_status=int(StatusPagamentoId.SOLICITADO), valor=pedido.valor_total)
    db.session.add(pagamento)
    db.session.commit()  # a tentativa fica registrada mesmo que o gateway falhe

    try:
        pagamento.id_transacao_externa = gateway.solicitar_pagamento(pedido.id, pedido.valor_total)
    except gateway.GatewayIndisponivel:
        pagamento.id_status = int(StatusPagamentoId.ERRO)
        pagamento.data_retorno = tempo.agora_utc()
        db.session.commit()
        raise ErroNegocio(
            "GATEWAY_INDISPONIVEL", "O gateway de pagamento está indisponível. Tente novamente em instantes.", 502,
            [{"id_pagamento": pagamento.id}],
        )
    pagamento.id_status = int(StatusPagamentoId.PROCESSANDO)
    auditoria_service.registrar(usuario, "PAGAMENTO_SOLICITADO", pedido.id, f"transacao={pagamento.id_transacao_externa}")
    db.session.commit()
    return pagamento


def registrar_retorno(dados: dict):
    """Chamado pelo gateway. É idempotente: repetir o mesmo resultado não muda nada."""
    pagamento = Pagamento.query.filter_by(id_transacao_externa=dados["id_transacao_externa"]).first()
    if not pagamento:
        raise ErroNegocio("TRANSACAO_NAO_ENCONTRADA", "Transação não encontrada.", 404)

    alvo = int(_RESULTADO_PARA_STATUS[dados["resultado"]])
    pedido = pagamento.pedido
    if pagamento.id_status == alvo:
        return pagamento, pedido, True
    if pagamento.id_status not in PAGAMENTO_EM_ANDAMENTO:
        raise ErroNegocio("RETORNO_CONFLITANTE", "Esta transação já foi finalizada com outro resultado.", 409)

    pagamento.id_status = alvo
    pagamento.data_retorno = tempo.agora_utc()
    if alvo == int(StatusPagamentoId.EFETUADO) and pedido.id_status == int(StatusPedidoId.AGUARDANDO_PAGAMENTO):
        pedido.id_status = int(StatusPedidoId.EM_PRODUCAO)
    auditoria_service.registrar(None, "PAGAMENTO_RETORNO", pedido.id, f"{dados['resultado']}; transacao={pagamento.id_transacao_externa}")
    db.session.commit()
    return pagamento, pedido, False


def listar_pagamentos(usuario: UsuarioAtual, id_pedido: int):
    pedido = obter_pedido(id_pedido)
    exigir_acesso(usuario, pedido)
    return sorted(pedido.pagamentos, key=lambda p: p.id)
