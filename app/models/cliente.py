"""Cliente do aplicativo."""
from datetime import date
from typing import Optional

from sqlalchemy.orm import Mapped, mapped_column, relationship
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db


class Cliente(db.Model):
    __tablename__ = "cliente"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(db.String(120), nullable=False)
    cpf: Mapped[str] = mapped_column(db.String(14), nullable=False, unique=True)
    email: Mapped[str] = mapped_column(db.String(120), nullable=False, unique=True)
    senha_hash: Mapped[str] = mapped_column(db.String(255), nullable=False)
    data_nascimento: Mapped[date] = mapped_column(db.Date, nullable=False)
    cidade: Mapped[Optional[str]] = mapped_column(db.String(80))

    pedidos = relationship("Pedido", back_populates="cliente")

    def definir_senha(self, senha: str) -> None:
        self.senha_hash = generate_password_hash(senha)

    def conferir_senha(self, senha: str) -> bool:
        return check_password_hash(self.senha_hash, senha)

    @property
    def idade(self) -> int:
        """A idade é calculada a partir da data de nascimento, nunca perguntada ao cliente."""
        hoje = date.today()
        n = self.data_nascimento
        return hoje.year - n.year - ((hoje.month, hoje.day) < (n.month, n.day))
