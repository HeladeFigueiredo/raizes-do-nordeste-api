"""Regras de negócio dos pedidos: criação, consulta com escopo por perfil, e status."""
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Optional

from app.constants import (
    PERFIL_MATRIZ, STATUS_PEDIDO_NOMES, TRANSICOES_PEDIDO, StatusPagamentoId, StatusPedidoId,
)
from app.errors import ErroNegocio
from app.extensions import db
from app.models import Cliente, ItemPedido, Pedido, ProdutoUnidade, Sabor
from app.security import UsuarioAtual, exigir_unidade
from app.services import auditoria_service, cardapio_service
from app.utils import tempo

CENTAVOS = Decimal("0.01")
PAGAMENTO_EM_ANDAMENTO = (int(StatusPagamentoId.SOLICITADO), int(StatusPagamentoId.PROCESSANDO))


# ---------- acesso ----------
def obter_pedido(id_pedido: int) -> Pedido:
    pedido = db.session.get(Pedido, id_pedido)
    if not pedido:
        raise ErroNegocio("PEDIDO_NAO_ENCONTRADO", "Pedido não encontrado.", 404)
    return pedido


def pode_acessar(usuario: UsuarioAtual, pedido: Pedido) -> bool:
    """Cliente vê só os seus. A equipe vê os da própria unidade. A matriz vê todos."""
    if usuario.e_cliente:
        return pedido.id_cliente == usuario.id
    if usuario.perfil == PERFIL_MATRIZ:
        return True
    return usuario.id_unidade == pedido.id_unidade


def exigir_acesso(usuario: UsuarioAtual, pedido: Pedido) -> None:
    if not pode_acessar(usuario, pedido):
        raise ErroNegocio("SEM_PERMISSAO", "Você não tem acesso a este pedido.", 403)


def tem_pagamento_em_andamento(pedido: Pedido) -> bool:
    return any(p.id_status in PAGAMENTO_EM_ANDAMENTO for p in pedido.pagamentos)


# ---------- criação ----------
def criar_pedido(usuario: UsuarioAtual, dados: dict) -> Pedido:
    unidade = cardapio_service.obter_unidade(dados["id_unidade"])
    canal = dados["canal"]

    if usuario.e_cliente:
        if canal == "BALCAO":
            raise ErroNegocio("CANAL_NAO_PERMITIDO", "O canal BALCAO é do atendimento humano. Use APP, TOTEM ou PICKUP.", 422)
        id_cliente = usuario.id  # o cliente logado é sempre o dono; qualquer id_cliente enviado é ignorado
    else:
        exigir_unidade(unidade.id)
        id_cliente = dados.get("id_cliente")
        if id_cliente is not None and not db.session.get(Cliente, id_cliente):
            raise ErroNegocio("CLIENTE_NAO_ENCONTRADO", "Cliente não encontrado.", 404)

    quantidades: dict = {}  # o mesmo sabor repetido na lista é somado
    for item in dados["itens"]:
        quantidades[item["id_sabor"]] = quantidades.get(item["id_sabor"], 0) + item["quantidade"]
    if any(q > 50 for q in quantidades.values()):
        raise ErroNegocio("QUANTIDADE_INVALIDA", "A quantidade total de um mesmo sabor não pode passar de 50.", 400)

    data = tempo.hoje()
    itens, problemas = [], []
    for id_sabor, quantidade in quantidades.items():
        sabor = db.session.get(Sabor, id_sabor)
        if not sabor:
            problemas.append({"id_sabor": id_sabor, "motivo": "SABOR_INEXISTENTE"})
            continue
        registro = ProdutoUnidade.query.filter_by(id_unidade=unidade.id, id_sabor=id_sabor).first()
        if not registro or not registro.esta_disponivel:
            problemas.append({"id_sabor": id_sabor, "motivo": "INDISPONIVEL_NA_UNIDADE"})
        elif not sabor.esta_na_estacao(data):
            problemas.append({"id_sabor": id_sabor, "motivo": "FORA_DE_ESTACAO"})
        else:
            # o preço é gravado no item: se o cardápio mudar depois, o histórico não muda
            itens.append(ItemPedido(id_sabor=id_sabor, quantidade=quantidade, preco_unitario=registro.preco_vigente()))
    if problemas:
        raise ErroNegocio("ITEM_INDISPONIVEL", "Há itens indisponíveis neste pedido.", 422, problemas)

    pedido = Pedido(
        id_cliente=id_cliente, id_unidade=unidade.id, canal=canal,
        id_status=int(StatusPedidoId.AGUARDANDO_PAGAMENTO), data_pedido=tempo.agora_utc(),
    )
    pedido.itens = itens
    pedido.valor_total = pedido.calcular_total().quantize(CENTAVOS)
    db.session.add(pedido)
    db.session.flush()
    auditoria_service.registrar(usuario, "PEDIDO_CRIADO", pedido.id, f"canalPedido={canal}; total={pedido.valor_total}")
    db.session.commit()
    return pedido


# ---------- consulta ----------
def listar_pedidos(usuario: UsuarioAtual, id_unidade: Optional[int], status: Optional[str],
                   data_inicio: Optional[date], data_fim: Optional[date], canal: Optional[str] = None):
    consulta = Pedido.query
    if usuario.e_cliente:
        consulta = consulta.filter(Pedido.id_cliente == usuario.id)
    elif usuario.perfil != PERFIL_MATRIZ:
        if id_unidade is not None and id_unidade != usuario.id_unidade:
            raise ErroNegocio("SEM_PERMISSAO", "Você só pode consultar pedidos da sua própria unidade.", 403)
        consulta = consulta.filter(Pedido.id_unidade == usuario.id_unidade)
    if id_unidade is not None:
        consulta = consulta.filter(Pedido.id_unidade == id_unidade)
    if canal:
        consulta = consulta.filter(Pedido.canal == canal)
    if status:
        consulta = consulta.filter(Pedido.id_status == int(StatusPedidoId[status]))
    if data_inicio:
        consulta = consulta.filter(Pedido.data_pedido >= datetime.combine(data_inicio, datetime.min.time()))
    if data_fim:  # inclusivo: vai até o fim do dia
        consulta = consulta.filter(Pedido.data_pedido < datetime.combine(data_fim + timedelta(days=1), datetime.min.time()))
    return consulta.order_by(Pedido.data_pedido.desc(), Pedido.id.desc())


# ---------- status ----------
def _nome(status: StatusPedidoId) -> str:
    return STATUS_PEDIDO_NOMES[status]


def avancar_status(usuario: UsuarioAtual, id_pedido: int, codigo: str) -> Pedido:
    """Avanço manual feito pela equipe: EM_PRODUCAO -> PRONTO -> RETIRADO."""
    pedido = obter_pedido(id_pedido)
    exigir_acesso(usuario, pedido)
    atual, novo = StatusPedidoId(pedido.id_status), StatusPedidoId[codigo]

    if novo == StatusPedidoId.EM_PRODUCAO:
        raise ErroNegocio("TRANSICAO_INVALIDA", "O pedido entra em produção sozinho quando o pagamento é confirmado.", 409)
    if novo not in TRANSICOES_PEDIDO[atual]:
        raise ErroNegocio("TRANSICAO_INVALIDA", f"Não é possível ir de «{_nome(atual)}» para «{_nome(novo)}».", 409)

    pedido.id_status = int(novo)
    auditoria_service.registrar(usuario, "STATUS_ALTERADO", pedido.id, f"{atual.name} -> {novo.name}")
    db.session.commit()
    return pedido
