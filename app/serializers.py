"""Conversão dos modelos para JSON. Valores em dinheiro saem como número com duas casas."""
from datetime import datetime
from decimal import Decimal
from typing import Optional

from app.constants import STATUS_PAGAMENTO_NOMES, STATUS_PEDIDO_NOMES, StatusPagamentoId, StatusPedidoId


def dinheiro(valor: Optional[Decimal]) -> Optional[float]:
    return None if valor is None else float(valor)


def datahora(valor: Optional[datetime]) -> Optional[str]:
    """Datas são guardadas em UTC e devolvidas em ISO 8601 com sufixo Z."""
    return None if valor is None else valor.replace(tzinfo=None).isoformat(timespec="seconds") + "Z"


def unidade_json(u) -> dict:
    return {"id": u.id, "nome": u.nome, "cidade": u.cidade, "regiao": u.regiao, "tipo_cozinha": u.tipo_cozinha}


def produto_json(p) -> dict:
    return {"id": p.id, "nome": p.nome, "descricao": p.descricao}


def sabor_json(s) -> dict:
    return {
        "id": s.id, "id_produto": s.id_produto, "nome": s.nome, "preco_base": dinheiro(s.preco_base),
        "data_inicio_venda": s.data_inicio_venda.isoformat() if s.data_inicio_venda else None,
        "data_fim_venda": s.data_fim_venda.isoformat() if s.data_fim_venda else None,
    }


def disponibilidade_json(pu) -> dict:
    return {
        "id_unidade": pu.id_unidade, "id_sabor": pu.id_sabor, "esta_disponivel": pu.esta_disponivel,
        "preco_local": dinheiro(pu.preco_local), "preco_vigente": dinheiro(pu.preco_vigente()),
    }


def status_pedido_json(id_status: int) -> dict:
    codigo = StatusPedidoId(id_status)
    return {"status": STATUS_PEDIDO_NOMES[codigo], "status_codigo": codigo.name}


def pagamento_json(p) -> dict:
    codigo = StatusPagamentoId(p.id_status)
    return {
        "id": p.id, "id_pedido": p.id_pedido, "status": STATUS_PAGAMENTO_NOMES[codigo], "status_codigo": codigo.name,
        "valor": dinheiro(p.valor), "id_transacao_externa": p.id_transacao_externa, "data_retorno": datahora(p.data_retorno),
    }


def item_pedido_json(i) -> dict:
    return {
        "id_sabor": i.id_sabor, "produto": i.sabor.produto.nome, "sabor": i.sabor.nome, "quantidade": i.quantidade,
        "preco_unitario": dinheiro(i.preco_unitario), "subtotal": dinheiro(i.subtotal()),
    }


def pedido_json(p, detalhado: bool = True) -> dict:
    corpo = {
        "id": p.id, "id_cliente": p.id_cliente, "id_unidade": p.id_unidade, "canalPedido": p.canal,
        **status_pedido_json(p.id_status), "valor_total": dinheiro(p.valor_total), "data_pedido": datahora(p.data_pedido),
    }
    if detalhado:
        corpo["itens"] = [item_pedido_json(i) for i in p.itens]
        corpo["pagamentos"] = [pagamento_json(x) for x in sorted(p.pagamentos, key=lambda x: x.id)]
    return corpo


def auditoria_json(a) -> dict:
    return {
        "id": a.id, "tipo_ator": a.tipo_ator, "id_ator": a.id_ator, "id_pedido": a.id_pedido,
        "acao": a.acao, "detalhe": a.detalhe, "data_acao": datahora(a.data_acao),
    }
