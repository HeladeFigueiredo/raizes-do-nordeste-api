"""Extensões do Flask, criadas aqui e ligadas ao app em create_app()."""
import sqlite3

from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import event
from sqlalchemy.engine import Engine

db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()


@event.listens_for(Engine, "connect")
def _ativar_chaves_estrangeiras_no_sqlite(conexao, _registro):
    """O SQLite ignora chaves estrangeiras por padrão. Ligamos para o desenvolvimento se comportar como o PostgreSQL."""
    if isinstance(conexao, sqlite3.Connection):
        cursor = conexao.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
