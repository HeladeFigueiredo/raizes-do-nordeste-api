"""Peças reutilizadas pelos schemas de validação."""
OBRIGATORIO = {"required": "Campo obrigatório.", "null": "Campo obrigatório."}


def campo(tipo, mensagem_invalido="Valor inválido.", **kwargs):
    """Cria um campo Marshmallow com mensagens de erro em português."""
    return tipo(error_messages={**OBRIGATORIO, "invalid": mensagem_invalido}, **kwargs)
