from flask import Blueprint, jsonify

from app.constants import PERFIL_MATRIZ
from app.schemas.cardapio import ProdutoSchema, SaborSchema
from app.security import perfis_permitidos
from app.serializers import produto_json, sabor_json
from app.services import cardapio_service as servico
from app.validacao import carregar

bp = Blueprint("produtos", __name__)


@bp.post("/produtos")
@perfis_permitidos(PERFIL_MATRIZ)
def criar_produto():
    return jsonify(produto_json(servico.criar_produto(carregar(ProdutoSchema())))), 201


@bp.post("/produtos/<int:id_produto>/sabores")
@perfis_permitidos(PERFIL_MATRIZ)
def criar_sabor(id_produto):
    """Cadastra um sabor com preço base e, opcionalmente, período de venda (sazonalidade)."""
    return jsonify(sabor_json(servico.criar_sabor(id_produto, carregar(SaborSchema())))), 201


@bp.put("/sabores/<int:id_sabor>")
@perfis_permitidos(PERFIL_MATRIZ)
def atualizar_sabor(id_sabor):
    """Atualização parcial: nome, preço base ou período de venda."""
    dados = carregar(SaborSchema(partial=True))
    return jsonify(sabor_json(servico.atualizar_sabor(id_sabor, dados)))
