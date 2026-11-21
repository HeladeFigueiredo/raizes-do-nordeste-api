"""Equipe, usuários e perfis de acesso."""
from typing import Optional

from sqlalchemy.orm import Mapped, mapped_column, relationship
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db


class Perfil(db.Model):
    __tablename__ = "perfil"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(db.String(30), nullable=False, unique=True)  # FUNCIONARIO, GERENTE, MATRIZ

    usuarios = relationship("Usuario", back_populates="perfil")


class Equipe(db.Model):
    __tablename__ = "equipe"

    id: Mapped[int] = mapped_column(primary_key=True)
    id_unidade: Mapped[Optional[int]] = mapped_column(db.ForeignKey("unidade.id"))  # nulo para a equipe da matriz
    nome: Mapped[str] = mapped_column(db.String(120), nullable=False)
    funcao: Mapped[str] = mapped_column(db.String(40), nullable=False)  # atendente, cozinheiro, gerente...
    cpf: Mapped[str] = mapped_column(db.String(14), nullable=False, unique=True)
    telefone: Mapped[Optional[str]] = mapped_column(db.String(20))

    unidade = relationship("Unidade", back_populates="equipe")
    usuario = relationship("Usuario", back_populates="equipe", uselist=False)


class Usuario(db.Model):
    __tablename__ = "usuario"

    id: Mapped[int] = mapped_column(primary_key=True)
    id_equipe: Mapped[int] = mapped_column(db.ForeignKey("equipe.id"), nullable=False, unique=True)
    id_perfil: Mapped[int] = mapped_column(db.ForeignKey("perfil.id"), nullable=False)
    login: Mapped[str] = mapped_column(db.String(80), nullable=False, unique=True)
    senha_hash: Mapped[str] = mapped_column(db.String(255), nullable=False)

    equipe = relationship("Equipe", back_populates="usuario")
    perfil = relationship("Perfil", back_populates="usuarios")

    def definir_senha(self, senha: str) -> None:
        self.senha_hash = generate_password_hash(senha)

    def conferir_senha(self, senha: str) -> bool:
        return check_password_hash(self.senha_hash, senha)

