"""Pedido, itens, pagamento (integração externa) e tabelas de status."""
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.constants import StatusPedidoId
from app.extensions import db
from app.models.base import agora


class StatusPedido(db.Model):
    __tablename__ = "status_pedido"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    nome: Mapped[str] = mapped_column(db.String(60), nullable=False, unique=True)


class StatusPagamento(db.Model):
    __tablename__ = "status_pagamento"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    nome: Mapped[str] = mapped_column(db.String(60), nullable=False, unique=True)


class Pedido(db.Model):
    __tablename__ = "pedido"

    id: Mapped[int] = mapped_column(primary_key=True)
    id_cliente: Mapped[Optional[int]] = mapped_column(db.ForeignKey("cliente.id"))  # nulo em venda de balcão sem cadastro
    id_unidade: Mapped[int] = mapped_column(db.ForeignKey("unidade.id"), nullable=False)
    id_status: Mapped[int] = mapped_column(
        db.ForeignKey("status_pedido.id"), nullable=False, default=int(StatusPedidoId.AGUARDANDO_PAGAMENTO)
    )
    canal: Mapped[str] = mapped_column(db.String(10), nullable=False)  # APP, TOTEM, BALCAO ou PICKUP
    valor_total: Mapped[Decimal] = mapped_column(db.Numeric(10, 2), nullable=False, default=0)
    data_pedido: Mapped[datetime] = mapped_column(nullable=False, default=agora)

    cliente = relationship("Cliente", back_populates="pedidos")
    unidade = relationship("Unidade", back_populates="pedidos")
    status = relationship("StatusPedido")
    itens = relationship("ItemPedido", back_populates="pedido", cascade="all, delete-orphan")
    pagamentos = relationship("Pagamento", back_populates="pedido", cascade="all, delete-orphan")

    def calcular_total(self) -> Decimal:
        return sum((item.subtotal() for item in self.itens), Decimal("0.00"))


class ItemPedido(db.Model):
    __tablename__ = "item_pedido"

    id: Mapped[int] = mapped_column(primary_key=True)
    id_pedido: Mapped[int] = mapped_column(db.ForeignKey("pedido.id"), nullable=False)
    id_sabor: Mapped[int] = mapped_column(db.ForeignKey("sabor.id"), nullable=False)
    quantidade: Mapped[int] = mapped_column(nullable=False)
    # Preço gravado no momento da compra, para o histórico não mudar se o preço for alterado depois
    preco_unitario: Mapped[Decimal] = mapped_column(db.Numeric(10, 2), nullable=False)

    pedido = relationship("Pedido", back_populates="itens")
    sabor = relationship("Sabor")

    def subtotal(self) -> Decimal:
        return self.preco_unitario * self.quantidade


class Pagamento(db.Model):
    """O sistema não processa pagamento: só solicita ao gateway e registra o resultado."""

    __tablename__ = "pagamento"

    id: Mapped[int] = mapped_column(primary_key=True)
    id_pedido: Mapped[int] = mapped_column(db.ForeignKey("pedido.id"), nullable=False)
    id_status: Mapped[int] = mapped_column(db.ForeignKey("status_pagamento.id"), nullable=False)
    id_transacao_externa: Mapped[Optional[str]] = mapped_column(db.String(80), unique=True)
    valor: Mapped[Decimal] = mapped_column(db.Numeric(10, 2), nullable=False)
    data_retorno: Mapped[Optional[datetime]] = mapped_column()

    pedido = relationship("Pedido", back_populates="pagamentos")
    status = relationship("StatusPagamento")
