from marshmallow import EXCLUDE, Schema, fields, validate

from app.constants import CANAIS_PEDIDO, StatusPedidoId
from app.schemas.comum import campo

INTEIRO = "Informe um número inteiro."


class ItemPedidoSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    id_sabor = campo(fields.Integer, INTEIRO, required=True, strict=True)
    quantidade = campo(fields.Integer, INTEIRO, required=True, strict=True,
                       validate=validate.Range(min=1, max=50, error="A quantidade deve ser entre 1 e 50."))


class PedidoSchema(Schema):
    class Meta:
        unknown = EXCLUDE  # valor_total, status e outros campos enviados pelo cliente são ignorados

    id_unidade = campo(fields.Integer, INTEIRO, required=True, strict=True)
    canal = campo(fields.String, required=True, data_key="canalPedido",
                  validate=validate.OneOf(CANAIS_PEDIDO, error="Canal inválido. Use APP, TOTEM, BALCAO, PICKUP ou WEB."))
    itens = campo(fields.List, "Envie uma lista de itens.", cls_or_instance=fields.Nested(ItemPedidoSchema), required=True,
                  validate=validate.Length(min=1, max=30, error="O pedido deve ter de 1 a 30 itens."))
    # Só a equipe usa: identifica o cliente de uma venda assistida. Para o cliente logado é ignorado.
    id_cliente = fields.Integer(strict=True, allow_none=True, load_default=None)


class StatusSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    status = campo(fields.String, required=True,
                   validate=validate.OneOf([s.name for s in StatusPedidoId], error="Status inválido."))


class RetornoPagamentoSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    id_transacao_externa = campo(fields.String, required=True, validate=validate.Length(min=1, max=80, error="Transação inválida."))
    resultado = campo(fields.String, required=True,
                      validate=validate.OneOf(("APROVADO", "NEGADO", "ERRO"), error="Use APROVADO, NEGADO ou ERRO."))
