"""Fonte unica de configuracao: tudo vem do ambiente, nada fica no codigo.

Fecha AP-02 (segredo hardcoded) e AP-07 (DEBUG fixo). Um `.env` na raiz do
projeto e carregado se existir, apenas como conveniencia de desenvolvimento --
variaveis ja presentes no ambiente tem precedencia.
"""

import os
from pathlib import Path

RAIZ_DO_PROJETO = Path(__file__).resolve().parents[2]
ARQUIVO_ENV = RAIZ_DO_PROJETO / ".env"


class ConfiguracaoAusente(RuntimeError):
    """Variavel de ambiente obrigatoria nao definida. Falha no boot, de proposito."""


def carregar_arquivo_env(caminho=ARQUIVO_ENV):
    if not caminho.exists():
        return
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        chave, _, valor = linha.partition("=")
        os.environ.setdefault(chave.strip(), valor.strip().strip('"').strip("'"))


def _obrigatorio(nome):
    valor = os.environ.get(nome, "").strip()
    if not valor:
        raise ConfiguracaoAusente(
            "Variavel de ambiente obrigatoria ausente: " + nome +
            ". Copie .env.example para .env e preencha os valores."
        )
    return valor


def _texto(nome, padrao):
    valor = os.environ.get(nome, "").strip()
    return valor or padrao


def _booleano(nome, padrao=False):
    valor = os.environ.get(nome)
    if valor is None or not valor.strip():
        return padrao
    return valor.strip().lower() in ("1", "true", "yes", "on", "sim")


def _inteiro(nome, padrao):
    valor = os.environ.get(nome, "").strip()
    if not valor:
        return padrao
    try:
        return int(valor)
    except ValueError:
        raise ConfiguracaoAusente(nome + " precisa ser um numero inteiro, recebido: " + valor)


def _lista(nome):
    valor = os.environ.get(nome, "").strip()
    if not valor:
        return []
    return [item.strip() for item in valor.split(",") if item.strip()]


class Settings:
    def __init__(self):
        self.secret_key = _obrigatorio("SECRET_KEY")
        self.db_path = _texto("DB_PATH", str(RAIZ_DO_PROJETO / "loja.db"))
        self.debug = _booleano("FLASK_DEBUG", False)
        self.host = _texto("HOST", "127.0.0.1")
        self.port = _inteiro("PORT", 5000)
        self.log_level = _texto("LOG_LEVEL", "INFO").upper()
        # Allowlist explicita (AP-16). Vazio = nenhum header CORS emitido.
        self.cors_origins = _lista("CORS_ORIGINS")
        self.token_ttl_segundos = _inteiro("TOKEN_TTL_SEGUNDOS", 3600)
        # Paginacao opcional: sem limite padrao para nao alterar o contrato das
        # listagens; o operador pode impor um teto por ambiente.
        self.listagem_limite_padrao = _inteiro("LISTAGEM_LIMITE_PADRAO", None)
        self.listagem_limite_maximo = _inteiro("LISTAGEM_LIMITE_MAXIMO", 500)
        # Rota destrutiva desligada por default (AP-06).
        self.admin_reset_habilitado = _booleano("ADMIN_RESET_HABILITADO", False)
        self.versao_api = _texto("VERSAO_API", "1.0.0")


def carregar_settings():
    carregar_arquivo_env()
    return Settings()
