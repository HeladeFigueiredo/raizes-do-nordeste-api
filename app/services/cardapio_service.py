"""Regras de negócio de unidades, produtos, sabores e cardápio por unidade."""
from datetime import date
from typing import Optional

from sqlalchemy import func

from app.errors import ErroNegocio
from app.extensions import db
from app.models import Produto, ProdutoUnidade, Sabor, Unidade
from app.serializers import dinheiro


# ---------- busca com 404 ----------
def obter_unidade(id_unidade: int) -> Unidade:
    unidade = db.session.get(Unidade, id_unidade)
    if not unidade:
        raise ErroNegocio("UNIDADE_NAO_ENCONTRADA", "Unidade não encontrada.", 404)
    return unidade


def obter_produto(id_produto: int) -> Produto:
    produto = db.session.get(Produto, id_produto)
    if not produto:
        raise ErroNegocio("PRODUTO_NAO_ENCONTRADO", "Produto não encontrado.", 404)
    return produto


def obter_sabor(id_sabor: int) -> Sabor:
    sabor = db.session.get(Sabor, id_sabor)
    if not sabor:
        raise ErroNegocio("SABOR_NAO_ENCONTRADO", "Sabor não encontrado.", 404)
    return sabor


# ---------- unidades ----------
def listar_unidades(cidade: Optional[str], regiao: Optional[str]):
    consulta = Unidade.query
    if cidade:
        consulta = consulta.filter(func.lower(Unidade.cidade) == cidade.strip().lower())
    if regiao:
        consulta = consulta.filter(func.lower(Unidade.regiao) == regiao.strip().lower())
    return consulta.order_by(Unidade.nome)


def criar_unidade(dados: dict) -> Unidade:
    unidade = Unidade(**dados)
    db.session.add(unidade)
    db.session.commit()
    return unidade


def atualizar_unidade(id_unidade: int, dados: dict) -> Unidade:
    unidade = obter_unidade(id_unidade)
    _exigir_campos(dados)
    for campo, valor in dados.items():
        setattr(unidade, campo, valor)
    db.session.commit()
    return unidade


# ---------- produtos e sabores ----------
def criar_produto(dados: dict) -> Produto:
    nome = dados["nome"].strip()
    if Produto.query.filter(func.lower(Produto.nome) == nome.lower()).first():
        raise ErroNegocio("PRODUTO_DUPLICADO", "Já existe um produto com este nome.", 409)
    produto = Produto(nome=nome, descricao=dados.get("descricao"))
    db.session.add(produto)
    db.session.commit()
    return produto


def criar_sabor(id_produto: int, dados: dict) -> Sabor:
    produto = obter_produto(id_produto)
    _exigir_sabor_unico(produto.id, dados["nome"])
    sabor = Sabor(id_produto=produto.id, **{**dados, "nome": dados["nome"].strip()})
    db.session.add(sabor)
    db.session.commit()
    return sabor


def atualizar_sabor(id_sabor: int, dados: dict) -> Sabor:
    sabor = obter_sabor(id_sabor)
    _exigir_campos(dados)
    if "nome" in dados:
        _exigir_sabor_unico(sabor.id_produto, dados["nome"], ignorar_id=sabor.id)
    inicio = dados.get("data_inicio_venda", sabor.data_inicio_venda)
    fim = dados.get("data_fim_venda", sabor.data_fim_venda)
    if inicio and fim and inicio > fim:  # a combinação com o que já estava gravado também precisa fazer sentido
        raise ErroNegocio("PERIODO_INVALIDO", "A data de início não pode ser depois da data de fim.", 400)
    for campo, valor in dados.items():
        setattr(sabor, campo, valor.strip() if campo == "nome" else valor)
    db.session.commit()
    return sabor


def _exigir_sabor_unico(id_produto: int, nome: str, ignorar_id: Optional[int] = None) -> None:
    consulta = Sabor.query.filter(Sabor.id_produto == id_produto, func.lower(Sabor.nome) == nome.strip().lower())
    if ignorar_id:
        consulta = consulta.filter(Sabor.id != ignorar_id)
    if consulta.first():
        raise ErroNegocio("SABOR_DUPLICADO", "Este produto já tem um sabor com este nome.", 409)


def _exigir_campos(dados: dict) -> None:
    if not dados:
        raise ErroNegocio("SEM_CAMPOS", "Envie ao menos um campo para atualizar.", 400)


# ---------- disponibilidade por unidade ----------
def definir_disponibilidade(id_unidade: int, id_sabor: int, dados: dict):
    """Cria ou atualiza o registro do sabor na unidade. Devolve (registro, criado)."""
    unidade = obter_unidade(id_unidade)
    sabor = obter_sabor(id_sabor)
    registro = ProdutoUnidade.query.filter_by(id_unidade=unidade.id, id_sabor=sabor.id).first()
    criado = registro is None
    if criado:
        registro = ProdutoUnidade(id_unidade=unidade.id, id_sabor=sabor.id)
        db.session.add(registro)
    registro.esta_disponivel = dados["esta_disponivel"]
    registro.preco_local = dados.get("preco_local")
    db.session.commit()
    return registro, criado


# ---------- cardápio ----------
def montar_cardapio(unidade: Unidade, data: date) -> dict:
    """Só entram os sabores disponíveis na unidade e dentro do período de venda na data."""
    consulta = (
        ProdutoUnidade.query.join(Sabor).join(Produto)
        .filter(ProdutoUnidade.id_unidade == unidade.id, ProdutoUnidade.esta_disponivel.is_(True))
        .order_by(Produto.nome, Sabor.nome)
    )
    grupos: dict = {}
    for registro in consulta.all():
        sabor = registro.sabor
        if not sabor.esta_na_estacao(data):
            continue
        produto = sabor.produto
        grupo = grupos.setdefault(produto.id, {
            "id_produto": produto.id, "produto": produto.nome, "descricao": produto.descricao, "sabores": [],
        })
        grupo["sabores"].append({"id_sabor": sabor.id, "sabor": sabor.nome, "preco": dinheiro(registro.preco_vigente())})
    return {"data_referencia": data.isoformat(), "itens": list(grupos.values())}
