"""Configurações por ambiente. Os valores sensíveis vêm de variáveis de ambiente (.env)."""
import os
from datetime import timedelta


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "troque-esta-chave-em-producao")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "troque-esta-chave-jwt-em-producao")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=int(os.getenv("JWT_EXPIRA_MINUTOS", "60")))
    # SQLite em desenvolvimento. Em produção, use PostgreSQL:
    # postgresql+psycopg2://usuario:senha@host:5432/raizes
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///raizes.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JSON_SORT_KEYS = False
    # Gateway de pagamento. O sistema NÃO processa pagamento: só solicita e registra o retorno.
    # O gateway chama POST /pagamentos/retorno enviando esta chave no cabeçalho X-API-Key.
    GATEWAY_API_KEY = os.getenv("GATEWAY_API_KEY", "chave-do-gateway-dev")
    GATEWAY_DISPONIVEL = True  # em desenvolvimento, False simula o gateway fora do ar
    # Senha dos usuários criados pelo comando "flask seed" (somente desenvolvimento)
    SEED_PASSWORD = os.getenv("SEED_PASSWORD", "senha123")


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
