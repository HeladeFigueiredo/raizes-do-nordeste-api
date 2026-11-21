"""Funções de tempo isoladas para poderem ser trocadas nos testes (ex.: simular o período junino)."""
from datetime import date, datetime, timezone


def hoje() -> date:
    return date.today()


def agora_utc() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)
