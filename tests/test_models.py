from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from app.constants import StatusPedidoId
from app.extensions import db
from app.models import (
    Cliente, ItemPedido, Pedido, Perfil, ProdutoUnidade, Sabor, StatusPedido, Unidade, Usuario,
)


def test_seed_cria_status_perfis_e_exemplos(seeded):
    assert StatusPedido.query.count() == 6
    assert {p.nome for p in Perfil.query.all()} == {"FUNCIONARIO", "GERENTE", "MATRIZ"}
    assert Unidade.query.count() == 2
    assert Usuario.query.count() == 3


def test_seed_e_idempotente(seeded):
    resultado = seeded.test_cli_runner().invoke(args=["seed"])
    assert resultado.exit_code == 0
    assert Unidade.query.count() == 2
    assert StatusPedido.query.count() == 6


def test_cliente_calcula_idade_e_guarda_senha_com_hash(app):
    hoje = date.today()
    cliente = Cliente(nome="Teste", cpf="000.000.000-00", email="t@t.com",
                      data_nascimento=date(hoje.year - 30, hoje.month, hoje.day))
    cliente.definir_senha("segredo")
    assert cliente.idade == 30
    assert cliente.senha_hash != "segredo"
    assert cliente.conferir_senha("segredo")
    assert not cliente.conferir_senha("outra")


def test_sazonalidade_do_sabor(app):
    sabor = Sabor(nome="Junino", preco_base=Decimal("7"),
                  data_inicio_venda=date(2026, 6, 1), data_fim_venda=date(2026, 7, 31))
    assert sabor.esta_na_estacao(date(2026, 6, 15))
    assert not sabor.esta_na_estacao(date(2026, 8, 1))
    assert not sabor.esta_na_estacao(date(2026, 5, 31))
    assert Sabor(nome="Fixo", preco_base=Decimal("5")).esta_na_estacao(date(2026, 1, 1))


def test_disponibilidade_por_unidade(seeded):
    quiosque = Unidade.query.filter_by(tipo_cozinha="REDUZIDA").one()
    boa_viagem = Unidade.query.filter_by(tipo_cozinha="COMPLETA").one()
    ovo = Sabor.query.filter_by(nome="Ovo com queijo").one()
    assert ProdutoUnidade.query.filter_by(id_unidade=boa_viagem.id, id_sabor=ovo.id).count() == 1
    assert ProdutoUnidade.query.filter_by(id_unidade=quiosque.id, id_sabor=ovo.id).count() == 0


def test_preco_local_substitui_preco_base(seeded):
    pu = ProdutoUnidade.query.first()
    base = pu.sabor.preco_base
    assert pu.preco_vigente() == base
    pu.preco_local = Decimal("9.90")
    assert pu.preco_vigente() == Decimal("9.90")


def test_sabor_repetido_na_mesma_unidade_e_barrado(seeded):
    pu = ProdutoUnidade.query.first()
    db.session.add(ProdutoUnidade(id_unidade=pu.id_unidade, id_sabor=pu.id_sabor))
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


def test_pedido_calcula_total_e_comeca_aguardando_pagamento(seeded):
    unidade = Unidade.query.first()
    cliente = Cliente.query.first()
    queijo = Sabor.query.filter_by(nome="Queijo").one()
    presunto = Sabor.query.filter_by(nome="Queijo com presunto").one()
    pedido = Pedido(id_cliente=cliente.id, id_unidade=unidade.id, canal="APP")
    pedido.itens = [
        ItemPedido(id_sabor=queijo.id, quantidade=1, preco_unitario=queijo.preco_base),
        ItemPedido(id_sabor=presunto.id, quantidade=2, preco_unitario=presunto.preco_base),
    ]
    db.session.add(pedido)
    db.session.commit()
    assert pedido.calcular_total() == Decimal("19.00")
    assert pedido.id_status == int(StatusPedidoId.AGUARDANDO_PAGAMENTO)


def test_cpf_duplicado_e_barrado(seeded):
    existente = Cliente.query.first()
    duplicado = Cliente(nome="Outro", cpf=existente.cpf, email="outro@x.com",
                        senha_hash="x", data_nascimento=date(2000, 1, 1))
    db.session.add(duplicado)
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()
