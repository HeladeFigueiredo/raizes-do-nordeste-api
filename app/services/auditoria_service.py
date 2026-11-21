"""Auditoria de ações sensíveis. O registro entra na mesma transação da ação auditada."""
from typing import Optional

from app.constants import PERFIL_MATRIZ
from app.extensions import db
from app.models import Auditoria, Pedido
from app.security import UsuarioAtual


def registrar(ator: Optional[UsuarioAtual], acao: str, id_pedido: Optional[int], detalhe: str = None) -> None:
    """Adiciona o registro à sessão. Quem chama faz o commit junto com a ação. Sem ator, o autor é o gateway."""
    if ator is None:
        tipo, id_ator = "GATEWAY", None
    else:
        tipo, id_ator = ("CLIENTE" if ator.e_cliente else "EQUIPE"), ator.id
    db.session.add(Auditoria(tipo_ator=tipo, id_ator=id_ator, id_pedido=id_pedido, acao=acao, detalhe=detalhe))


def listar(usuario: UsuarioAtual, id_pedido: Optional[int], acao: Optional[str]):
    """Matriz vê tudo. O gerente vê apenas os registros de pedidos da própria unidade."""
    consulta = Auditoria.query
    if usuario.perfil != PERFIL_MATRIZ:
        consulta = consulta.join(Pedido, Pedido.id == Auditoria.id_pedido).filter(Pedido.id_unidade == usuario.id_unidade)
    if id_pedido is not None:
        consulta = consulta.filter(Auditoria.id_pedido == id_pedido)
    if acao:
        consulta = consulta.filter(Auditoria.acao == acao.upper())
    return consulta.order_by(Auditoria.id.desc())
