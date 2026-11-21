"""Validação e formatação de CPF."""
import re


def somente_digitos(valor: str) -> str:
    return re.sub(r"\D", "", valor or "")


def cpf_valido(cpf: str) -> bool:
    d = somente_digitos(cpf)
    if len(d) != 11 or d == d[0] * 11:
        return False
    for tamanho in (9, 10):
        soma = sum(int(d[i]) * (tamanho + 1 - i) for i in range(tamanho))
        digito = (soma * 10 % 11) % 10
        if digito != int(d[tamanho]):
            return False
    return True


def formatar_cpf(cpf: str) -> str:
    d = somente_digitos(cpf)
    return f"{d[:3]}.{d[3:6]}.{d[6:9]}-{d[9:]}"


def mascarar_cpf(cpf: str) -> str:
    """Mostra só os dois últimos dígitos (minimização de dados, LGPD)."""
    d = somente_digitos(cpf)
    return f"***.***.***-{d[9:]}" if len(d) == 11 else "***"
