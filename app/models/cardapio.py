"""Unidades, cardápio, e disponibilidade por loja."""
from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db


class Unidade(db.Model):
    __tablename__ = "unidade"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(db.String(100), nullable=False)
    cidade: Mapped[str] = mapped_column(db.String(80), nullable=False)
    regiao: Mapped[str] = mapped_column(db.String(40), nullable=False)
    tipo_cozinha: Mapped[str] = mapped_column(db.String(20), nullable=False, default="COMPLETA")  # COMPLETA ou REDUZIDA

    produtos_unidade = relationship("ProdutoUnidade", back_populates="unidade", cascade="all, delete-orphan")
    pedidos = relationship("Pedido", back_populates="unidade")
    equipe = relationship("Equipe", back_populates="unidade")


class Produto(db.Model):
    """Item do cardápio (ex.: tapioca, cuscuz recheado)."""

    __tablename__ = "produto"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(db.String(80), nullable=False, unique=True)
    descricao: Mapped[Optional[str]] = mapped_column(db.String(255))

    sabores = relationship("Sabor", back_populates="produto", cascade="all, delete-orphan")


class Sabor(db.Model):
    __tablename__ = "sabor"
    __table_args__ = (UniqueConstraint("id_produto", "nome", name="uq_produto_sabor"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    id_produto: Mapped[int] = mapped_column(db.ForeignKey("produto.id"), nullable=False)
    nome: Mapped[str] = mapped_column(db.String(80), nullable=False)
    preco_base: Mapped[Decimal] = mapped_column(db.Numeric(10, 2), nullable=False)
    # Sazonalidade: se ambas forem nulas, o sabor é vendido o ano todo
    data_inicio_venda: Mapped[Optional[date]] = mapped_column(db.Date)
    data_fim_venda: Mapped[Optional[date]] = mapped_column(db.Date)

    produto = relationship("Produto", back_populates="sabores")
    produtos_unidade = relationship("ProdutoUnidade", back_populates="sabor")

    def esta_na_estacao(self, data: Optional[date] = None) -> bool:
        """True se a data cai dentro do período de venda (ou se não há período definido)."""
        data = data or date.today()
        if self.data_inicio_venda and data < self.data_inicio_venda:
            return False
        if self.data_fim_venda and data > self.data_fim_venda:
            return False
        return True


class ProdutoUnidade(db.Model):
    """Quais sabores cada unidade oferece, com disponibilidade e preço local opcionais."""

    __tablename__ = "produto_unidade"
    __table_args__ = (UniqueConstraint("id_unidade", "id_sabor", name="uq_unidade_sabor"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    id_unidade: Mapped[int] = mapped_column(db.ForeignKey("unidade.id"), nullable=False)
    id_sabor: Mapped[int] = mapped_column(db.ForeignKey("sabor.id"), nullable=False)
    esta_disponivel: Mapped[bool] = mapped_column(nullable=False, default=True)
    preco_local: Mapped[Optional[Decimal]] = mapped_column(db.Numeric(10, 2))

    unidade = relationship("Unidade", back_populates="produtos_unidade")
    sabor = relationship("Sabor", back_populates="produtos_unidade")

    def preco_vigente(self) -> Decimal:
        return self.preco_local if self.preco_local is not None else self.sabor.preco_base

