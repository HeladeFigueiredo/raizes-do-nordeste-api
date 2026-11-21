from datetime import date

from flask import Blueprint, jsonify, request

from app.constants import PERFIL_GERENTE, PERFIL_MATRIZ
from app.errors import ErroNegocio
from app.schemas.cardapio import DisponibilidadeSchema, UnidadeSchema
from app.security import exigir_unidade, perfis_permitidos
from app.serializers import disponibilidade_json, unidade_json
from app.services import cardapio_service as servico
from app.utils.paginacao import paginar, parametros_paginacao
from app.validacao import carregar, corpo_json

bp = Blueprint("unidades", __name__)


@bp.get("/unidades")
def listar_unidades():
    """Lista unidades, com filtros ?cidade= e ?regiao= e paginação."""
    pagina, tamanho = parametros_paginacao()
    consulta = servico.listar_unidades(request.args.get("cidade"), request.args.get("regiao"))
    unidades, total = paginar(consulta, pagina, tamanho)
    return jsonify({"itens": [unidade_json(u) for u in unidades], "pagina": pagina, "tamanho": tamanho, "total": total})


@bp.post("/unidades")
@perfis_permitidos(PERFIL_MATRIZ)
def criar_unidade():
    unidade = servico.criar_unidade(carregar(UnidadeSchema()))
    return jsonify(unidade_json(unidade)), 201


@bp.put("/unidades/<int:id_unidade>")
@perfis_permitidos(PERFIL_MATRIZ)
def atualizar_unidade(id_unidade):
    """Atualização parcial: envie apenas os campos que mudam."""
    dados = carregar(UnidadeSchema(partial=True))
    return jsonify(unidade_json(servico.atualizar_unidade(id_unidade, dados)))


@bp.get("/unidades/<int:id_unidade>/cardapio")
def cardapio(id_unidade):
    """Cardápio da unidade hoje. O parâmetro ?data=AAAA-MM-DD simula outra data (útil para o período junino)."""
    unidade = servico.obter_unidade(id_unidade)
    texto = request.args.get("data")
    try:
        data = date.fromisoformat(texto) if texto else date.today()
    except ValueError:
        raise ErroNegocio("PARAMETRO_INVALIDO", "Use o formato AAAA-MM-DD em 'data'.", 400)
    return jsonify({"unidade": unidade_json(unidade), **servico.montar_cardapio(unidade, data)})


@bp.put("/unidades/<int:id_unidade>/sabores/<int:id_sabor>")
@perfis_permitidos(PERFIL_GERENTE, PERFIL_MATRIZ)
def definir_disponibilidade(id_unidade, id_sabor):
    """Gerente (da própria unidade) ou matriz definem disponibilidade e preço local de um sabor.
    Sem preco_local, o sabor volta a usar o preço base. Cria o registro se ainda não existir."""
    exigir_unidade(id_unidade)
    dados = carregar(DisponibilidadeSchema())
    registro, criado = servico.definir_disponibilidade(id_unidade, id_sabor, dados)
    return jsonify(disponibilidade_json(registro)), (201 if criado else 200)
