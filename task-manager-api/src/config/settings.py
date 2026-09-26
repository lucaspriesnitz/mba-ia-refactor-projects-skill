"""Fonte única de configuração: tudo vem do ambiente, nada fica no código.

Fecha AP-02 (`SECRET_KEY` e URI do banco literais em `app.py:11-13`, credenciais
SMTP em `services/notification_service.py:7-10`) e AP-07 (`debug=True` e
`host='0.0.0.0'` fixos em `app.py:34`). Um `.env` na raiz do projeto é carregado
se existir, só como conveniência de desenvolvimento -- variáveis já presentes no
ambiente têm precedência.
"""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = PROJECT_ROOT / ".env"


class MissingConfiguration(RuntimeError):
    """Variável obrigatória ausente ou inválida. Falha no boot, de propósito."""


def _required(name):
    value = os.environ.get(name, "").strip()
    if not value:
        raise MissingConfiguration(
            f"Variável de ambiente obrigatória ausente: {name}. "
            "Copie .env.example para .env e preencha os valores."
        )
    return value


def _text(name, default):
    return os.environ.get(name, "").strip() or default


def _boolean(name, default=False):
    value = os.environ.get(name, "").strip()
    if not value:
        return default
    return value.lower() in ("1", "true", "yes", "on")


def _integer(name, default):
    value = os.environ.get(name, "").strip()
    if not value:
        return default
    try:
        return int(value)
    except ValueError:
        raise MissingConfiguration(f"{name} precisa ser um número inteiro, recebido: {value}")


def _list(name):
    value = os.environ.get(name, "").strip()
    return [item.strip() for item in value.split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    secret_key: str
    database_url: str
    debug: bool
    host: str
    port: int
    log_level: str
    cors_origins: list
    token_ttl_seconds: int
    password_min_length: int
    list_default_limit: int | None
    list_max_limit: int


def load_settings():
    load_dotenv(ENV_FILE, override=False)

    secret_key = _required("SECRET_KEY")
    if len(secret_key) < 32:
        raise MissingConfiguration("SECRET_KEY precisa ter pelo menos 32 caracteres.")

    return Settings(
        secret_key=secret_key,
        # Relativo = dentro de instance/, como o 'sqlite:///tasks.db' original.
        database_url=_text("DATABASE_URL", "sqlite:///tasks.db"),
        debug=_boolean("FLASK_DEBUG", False),
        host=_text("HOST", "127.0.0.1"),
        port=_integer("PORT", 5000),
        log_level=_text("LOG_LEVEL", "INFO").upper(),
        cors_origins=_list("CORS_ORIGINS"),
        token_ttl_seconds=_integer("TOKEN_TTL_SECONDS", 3600),
        password_min_length=_integer("PASSWORD_MIN_LENGTH", 12),
        # Vazio = sem limite, que é o contrato original das listagens.
        list_default_limit=_integer("LIST_DEFAULT_LIMIT", None),
        list_max_limit=_integer("LIST_MAX_LIMIT", 500),
    )
