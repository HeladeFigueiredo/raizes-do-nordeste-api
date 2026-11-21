from decimal import Decimal

from marshmallow import EXCLUDE, Schema, ValidationError, fields, validate, validates_schema

from app.schemas.comum import campo

PRECO_MSG = "O preço deve estar entre 0,01 e 9999,99."
TIPOS_COZINHA = ("COMPLETA", "REDUZIDA")


def _preco(**kwargs):
    return campo(
        fields.Decimal, "Informe um número, por exemplo 7.50.", places=2, as_string=False,
        validate=validate.Range(min=Decimal("0.01"), max=Decimal("9999.99"), error=PRECO_MSG), **kwargs,
    )


class UnidadeSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    nome = campo(fields.String, required=True, validate=validate.Length(min=3, max=100, error="O nome deve ter entre 3 e 100 caracteres."))
    cidade = campo(fields.String, required=True, validate=validate.Length(min=2, max=80, error="A cidade deve ter entre 2 e 80 caracteres."))
    regiao = campo(fields.String, required=True, validate=validate.Length(min=2, max=40, error="A região deve ter entre 2 e 40 caracteres."))
    tipo_cozinha = campo(fields.String, required=True, validate=validate.OneOf(TIPOS_COZINHA, error="Use COMPLETA ou REDUZIDA."))


class ProdutoSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    nome = campo(fields.String, required=True, validate=validate.Length(min=2, max=80, error="O nome deve ter entre 2 e 80 caracteres."))
    descricao = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=255, error="A descrição deve ter até 255 caracteres."))


class SaborSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    nome = campo(fields.String, required=True, validate=validate.Length(min=2, max=80, error="O nome deve ter entre 2 e 80 caracteres."))
    preco_base = _preco(required=True)
    # Sazonalidade: sem datas, o sabor é vendido o ano todo
    data_inicio_venda = campo(fields.Date, "Use o formato AAAA-MM-DD.", allow_none=True, load_default=None)
    data_fim_venda = campo(fields.Date, "Use o formato AAAA-MM-DD.", allow_none=True, load_default=None)

    @validates_schema
    def _periodo(self, dados, **kwargs):
        inicio, fim = dados.get("data_inicio_venda"), dados.get("data_fim_venda")
        if inicio and fim and inicio > fim:
            raise ValidationError("A data de início não pode ser depois da data de fim.", "data_inicio_venda")


class DisponibilidadeSchema(Schema):
    """Disponibilidade de um sabor em uma unidade. Sem preco_local, vale o preço base."""

    class Meta:
        unknown = EXCLUDE

    esta_disponivel = campo(fields.Boolean, "Use true ou false.", required=True)
    preco_local = _preco(allow_none=True, load_default=None)
