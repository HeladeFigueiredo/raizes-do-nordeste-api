from flask import Blueprint, jsonify, request

from app.constants import PERFIL_GERENTE, PERFIL_MATRIZ
from app.errors import ErroNegocio
from app.security import perfis_permitidos, usuario_atual
from app.serializers import auditoria_json
from app.services import auditoria_service
from app.utils.paginacao import paginar, parametros_paginacao

bp = Blueprint("auditoria", __name__)


@bp.get("/auditoria")
@perfis_permitidos(PERFIL_GERENTE, PERFIL_MATRIZ)
def listar_auditoria():
    """Registros de ações sensíveis (mais recentes primeiro). Filtros: id_pedido, acao. Gerente vê só a própria unidade."""
    pagina, tamanho = parametros_paginacao()
    try:
        id_pedido = int(request.args["id_pedido"]) if request.args.get("id_pedido") else None
    except ValueError:
        raise ErroNegocio("PARAMETRO_INVALIDO", "'id_pedido' deve ser um número inteiro.", 400)
    consulta = auditoria_service.listar(usuario_atual(), id_pedido, request.args.get("acao"))
    registros, total = paginar(consulta, pagina, tamanho)
    return jsonify({"itens": [auditoria_json(a) for a in registros], "pagina": pagina, "tamanho": tamanho, "total": total})
