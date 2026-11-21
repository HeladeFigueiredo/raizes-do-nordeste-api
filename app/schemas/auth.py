from datetime import date, timedelta

from marshmallow import EXCLUDE, Schema, ValidationError, fields, validate, validates

from app.schemas.comum import campo as _campo
from app.utils.cpf import cpf_valido


class CadastroSchema(Schema):
    class Meta:
        unknown = EXCLUDE  # campos desconhecidos são ignorados (nada é copiado direto para o modelo)

    nome = _campo(fields.String, required=True, validate=validate.Length(min=3, max=120, error="O nome deve ter entre 3 e 120 caracteres."))
    cpf = _campo(fields.String, required=True)
    email = _campo(fields.Email, "E-mail inválido.", required=True)
    senha = _campo(fields.String, required=True, validate=validate.Length(min=8, max=72, error="A senha deve ter entre 8 e 72 caracteres."))
    data_nascimento = _campo(fields.Date, "Use o formato AAAA-MM-DD.", required=True)
    consentimento_lgpd = _campo(fields.Boolean, "Use true ou false.", required=True, truthy={True}, falsy={False})
    cidade = fields.String(load_default=None, validate=validate.Length(max=80, error="A cidade deve ter até 80 caracteres."))

    @validates("consentimento_lgpd")
    def _valida_consentimento(self, valor, **kwargs):
        if valor is not True:
            raise ValidationError("É necessário aceitar o tratamento dos dados pessoais (LGPD) para se cadastrar.")

    @validates("cpf")
    def _valida_cpf(self, valor, **kwargs):
        if not cpf_valido(valor):
            raise ValidationError("CPF inválido.")

    @validates("data_nascimento")
    def _valida_nascimento(self, valor, **kwargs):
        if valor > date.today():
            raise ValidationError("A data de nascimento não pode ser futura.")
        if valor < date.today() - timedelta(days=365 * 120):
            raise ValidationError("Data de nascimento inválida.")


class LoginSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    login = _campo(fields.String, required=True, validate=validate.Length(min=1, max=120, error="Informe o login."))
    senha = _campo(fields.String, required=True, validate=validate.Length(min=1, max=72, error="Informe a senha."))
