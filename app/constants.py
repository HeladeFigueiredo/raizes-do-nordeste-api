"""Constantes de negócio. Os ids devem coincidir com os dados criados pelo "flask seed"."""
from enum import IntEnum


class StatusPedidoId(IntEnum):
    AGUARDANDO_PAGAMENTO = 1
    EM_PRODUCAO = 2
    PRONTO = 3
    RETIRADO = 4
    CANCELADO_EMPRESA = 5
    CANCELADO_CLIENTE = 6


class StatusPagamentoId(IntEnum):
    SOLICITADO = 1
    PROCESSANDO = 2
    ERRO = 3
    NAO_APROVADO = 4
    EFETUADO = 5


STATUS_PEDIDO_NOMES = {
    StatusPedidoId.AGUARDANDO_PAGAMENTO: "Aguardando liberação do pagamento",
    StatusPedidoId.EM_PRODUCAO: "Em produção",
    StatusPedidoId.PRONTO: "Pedido pronto, pode retirar",
    StatusPedidoId.RETIRADO: "Pedido retirado",
    StatusPedidoId.CANCELADO_EMPRESA: "Pedido cancelado pela empresa",
    StatusPedidoId.CANCELADO_CLIENTE: "Pedido cancelado pelo cliente",
}

STATUS_PAGAMENTO_NOMES = {
    StatusPagamentoId.SOLICITADO: "Pagamento solicitado",
    StatusPagamentoId.PROCESSANDO: "Processando pagamento",
    StatusPagamentoId.ERRO: "Erro ao realizar o pagamento",
    StatusPagamentoId.NAO_APROVADO: "Pagamento não aprovado",
    StatusPagamentoId.EFETUADO: "Pagamento efetuado",
}

# Transições permitidas do status do pedido (usado na fatia do fluxo de pedidos)
TRANSICOES_PEDIDO = {
    StatusPedidoId.AGUARDANDO_PAGAMENTO: {StatusPedidoId.EM_PRODUCAO},
    StatusPedidoId.EM_PRODUCAO: {StatusPedidoId.PRONTO},
    StatusPedidoId.PRONTO: {StatusPedidoId.RETIRADO},
    StatusPedidoId.RETIRADO: set(),
    StatusPedidoId.CANCELADO_EMPRESA: set(),  # status reservados para a evolução futura (cancelamento)
    StatusPedidoId.CANCELADO_CLIENTE: set(),
}

CANAIS_PEDIDO = ("APP", "TOTEM", "BALCAO", "PICKUP", "WEB")

PERFIL_FUNCIONARIO = "FUNCIONARIO"
PERFIL_GERENTE = "GERENTE"
PERFIL_MATRIZ = "MATRIZ"
PERFIL_CLIENTE = "CLIENTE"  # não está na tabela perfil: o cliente tem cadastro próprio
PERFIS_EQUIPE = (PERFIL_FUNCIONARIO, PERFIL_GERENTE, PERFIL_MATRIZ)
