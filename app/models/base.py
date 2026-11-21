from datetime import datetime, timezone


def agora():
    """Data e hora atuais em UTC (usada como valor padrão das colunas de data)."""
    return datetime.now(timezone.utc)
