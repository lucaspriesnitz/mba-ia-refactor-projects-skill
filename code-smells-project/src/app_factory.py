"""Composition root: monta o grafo de dependências e devolve o app Flask.

Ordem: configuração (do ambiente) -> logging -> banco/schema -> container ->
CORS -> error handler -> rotas. Nada de segredo, caminho de arquivo ou flag de
dev escrito no código.
"""

import logging

from flask import Flask
from flask_cors import CORS

from .config import carregar_settings
from .container import Container
from .database.connection import Database
from .database.request_scope import criar_provedor_de_conexao, registrar_encerramento
from .database.schema import criar_schema
from .middlewares.error_handler import registrar_tratamento_de_erros
from .middlewares.logging_config import configurar_logging
from .routers import registrar_rotas
from .services.auth_service import AuthService

logger = logging.getLogger(__name__)


def criar_app(settings=None):
    settings = settings or carregar_settings()
    configurar_logging(settings.log_level)

    app = Flask(__name__)
    app.config["DEBUG"] = settings.debug          # AP-07: vem do ambiente
    app.config["SECRET_KEY"] = settings.secret_key  # AP-02: vem do ambiente

    database = Database(settings.db_path)
    _inicializar_banco(database, settings)

    provedor_conexao = criar_provedor_de_conexao(database)
    registrar_encerramento(app)

    app.extensions["container"] = Container(settings, provedor_conexao)

    _configurar_cors(app, settings)
    registrar_tratamento_de_erros(app)
    registrar_rotas(app)

    logger.info("Aplicação inicializada (debug=%s)", settings.debug)
    return app


def _inicializar_banco(database, settings):
    """Cria schema e seed fora do ciclo de requisição, com conexão própria."""
    auth = AuthService(settings.secret_key, settings.token_ttl_segundos)
    conexao = database.conectar()
    try:
        criar_schema(conexao, auth.gerar_hash_de_senha)
    finally:
        conexao.close()


def _configurar_cors(app, settings):
    """AP-16: allowlist explícita em vez de `CORS(app)` (equivalente a `*`).

    Sem `CORS_ORIGINS` definido, nenhum header de CORS é emitido -- default
    fechado. O valor é uma lista de origens separadas por vírgula.
    """
    if not settings.cors_origins:
        logger.info("CORS desabilitado (CORS_ORIGINS não configurado)")
        return
    CORS(app, origins=settings.cors_origins)
    logger.info("CORS habilitado para: %s", ", ".join(settings.cors_origins))
