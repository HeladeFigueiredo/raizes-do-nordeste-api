"""Fábrica da aplicação Flask (padrão application factory)."""
from flask import Flask

from app.config import Config
from app.extensions import db, jwt, migrate


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    app.json.sort_keys = False  # mantém a ordem dos campos como foram escritos

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)

    from app import models  # noqa: F401  (registra as tabelas para as migrações)
    from app.cli import registrar_comandos
    from app.errors import registrar_erros
    from app.routes import registrar_rotas
    from app.security import registrar_respostas_jwt

    registrar_respostas_jwt()

    registrar_rotas(app)
    registrar_erros(app)
    registrar_comandos(app)

    return app
