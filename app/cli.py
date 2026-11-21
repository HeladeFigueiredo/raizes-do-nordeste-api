"""Comandos de linha de comando. Uso: flask seed"""
from datetime import date
from decimal import Decimal

import click

from app.constants import (
    PERFIS_EQUIPE, STATUS_PAGAMENTO_NOMES, STATUS_PEDIDO_NOMES,
)
from app.extensions import db
from app.models import (
    Cliente, Equipe, Perfil, Produto, ProdutoUnidade,
    Sabor, StatusPagamento, StatusPedido, Unidade, Usuario,
)


def _tabelas_de_apoio():
    """Status e perfis: dados fixos de que o sistema depende para funcionar."""
    for id_, nome in STATUS_PEDIDO_NOMES.items():
        if not db.session.get(StatusPedido, int(id_)):
            db.session.add(StatusPedido(id=int(id_), nome=nome))
    for id_, nome in STATUS_PAGAMENTO_NOMES.items():
        if not db.session.get(StatusPagamento, int(id_)):
            db.session.add(StatusPagamento(id=int(id_), nome=nome))
    for nome in PERFIS_EQUIPE:
        if not Perfil.query.filter_by(nome=nome).first():
            db.session.add(Perfil(nome=nome))
    db.session.commit()


def _dados_de_exemplo(senha: str):
    """Unidades, cardápio e usuários de exemplo para desenvolvimento e demonstração."""
    if Unidade.query.first():
        return False

    boa_viagem = Unidade(nome="Raízes Boa Viagem", cidade="Recife", regiao="Litoral", tipo_cozinha="COMPLETA")
    quiosque = Unidade(nome="Raízes Quiosque Shopping", cidade="Recife", regiao="Litoral", tipo_cozinha="REDUZIDA")
    db.session.add_all([boa_viagem, quiosque])

    tapioca = Produto(nome="Tapioca", descricao="Tapioca recheada, o puro sabor do Nordeste")
    cuscuz = Produto(nome="Cuscuz recheado", descricao="Cuscuz com recheios regionais")
    bolo = Produto(nome="Bolo de macaxeira", descricao="Bolo tradicional de macaxeira")
    suco = Produto(nome="Suco regional", descricao="Sucos de frutas da região")
    db.session.add_all([tapioca, cuscuz, bolo, suco])
    db.session.flush()

    ano = date.today().year
    sabores = {
        "tap_queijo": Sabor(id_produto=tapioca.id, nome="Queijo", preco_base=Decimal("5.00")),
        "tap_presunto": Sabor(id_produto=tapioca.id, nome="Queijo com presunto", preco_base=Decimal("7.00")),
        "tap_ovo": Sabor(id_produto=tapioca.id, nome="Ovo com queijo", preco_base=Decimal("8.00")),
        "cus_carne": Sabor(id_produto=cuscuz.id, nome="Carne de sol", preco_base=Decimal("12.00")),
        "bolo_mac": Sabor(id_produto=bolo.id, nome="Tradicional", preco_base=Decimal("6.00")),
        "bolo_milho": Sabor(  # item sazonal do período junino
            id_produto=bolo.id, nome="Bolo de milho (junino)", preco_base=Decimal("7.00"),
            data_inicio_venda=date(ano, 6, 1), data_fim_venda=date(ano, 7, 31),
        ),
        "suco_caju": Sabor(id_produto=suco.id, nome="Caju", preco_base=Decimal("6.00")),
    }
    db.session.add_all(sabores.values())
    db.session.flush()

    # Boa Viagem (cozinha completa) oferece tudo. O quiosque (reduzido) não faz ovo com queijo nem cuscuz.
    for chave, sabor in sabores.items():
        db.session.add(ProdutoUnidade(id_unidade=boa_viagem.id, id_sabor=sabor.id, esta_disponivel=True))
        if chave not in ("tap_ovo", "cus_carne"):
            db.session.add(ProdutoUnidade(id_unidade=quiosque.id, id_sabor=sabor.id, esta_disponivel=True))

    perfis = {p.nome: p for p in Perfil.query.all()}
    equipe_exemplo = [
        ("Maria Atendente", "atendente", "111.111.111-11", boa_viagem, "funcionario", "FUNCIONARIO"),
        ("João Gerente", "gerente", "222.222.222-22", boa_viagem, "gerente", "GERENTE"),
        ("Ana Matriz", "administradora", "333.333.333-33", None, "matriz", "MATRIZ"),
    ]
    for nome, funcao, cpf, unidade, login, perfil in equipe_exemplo:
        membro = Equipe(nome=nome, funcao=funcao, cpf=cpf, id_unidade=unidade.id if unidade else None)
        db.session.add(membro)
        db.session.flush()
        usuario = Usuario(id_equipe=membro.id, id_perfil=perfis[perfil].id, login=login)
        usuario.definir_senha(senha)
        db.session.add(usuario)

    cliente = Cliente(nome="Cliente Exemplo", cpf="444.444.444-44", email="cliente@exemplo.com",
                      data_nascimento=date(1995, 5, 20), cidade="Recife")
    cliente.definir_senha(senha)
    db.session.add(cliente)

    db.session.commit()
    return True


def registrar_comandos(app):
    @app.cli.command("seed")
    @click.option("--sem-exemplos", is_flag=True, help="Cria só status e perfis, sem dados de exemplo.")
    def seed(sem_exemplos):
        """Popula o banco com status, perfis e (opcionalmente) dados de exemplo."""
        _tabelas_de_apoio()
        click.echo("Status e perfis garantidos.")
        if sem_exemplos:
            return
        if _dados_de_exemplo(app.config["SEED_PASSWORD"]):
            click.echo("Dados de exemplo criados. Logins: funcionario, gerente, matriz e cliente@exemplo.com")
        else:
            click.echo("Já existem dados no banco. Exemplos não foram recriados.")
