import pytest

from app import create_app
from app.config import TestingConfig
from app.extensions import db


@pytest.fixture()
def app():
    app = create_app(TestingConfig)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def seeded(app):
    """Banco com status, perfis e os dados de exemplo do comando 'flask seed'."""
    runner = app.test_cli_runner()
    resultado = runner.invoke(args=["seed"])
    assert resultado.exit_code == 0, resultado.output
    return app
