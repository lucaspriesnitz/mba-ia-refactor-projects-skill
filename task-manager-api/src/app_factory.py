"""Composition root: `create_app()` monta o grafo e devolve o app Flask.

Antes, importar `app.py` criava o app no escopo de módulo, lia config literal,
registrava rotas e rodava `db.create_all()` (`app.py:9-31`). Agora nada disso é
efeito de import: a app é construída sob demanda, com config do ambiente, e o
schema só muda por migration explícita.
"""

import logging

from flask import Flask
from flask_cors import CORS

from .config import PROJECT_ROOT, load_settings
from .container import Container
from .database import init_database
from .middlewares import configure_logging, register_error_handlers
from .routers import register_routes

logger = logging.getLogger(__name__)


def create_app(settings=None):
    settings = settings or load_settings()
    configure_logging(settings.log_level)

    app = Flask(__name__, instance_path=str(PROJECT_ROOT / "instance"))
    app.config["SECRET_KEY"] = settings.secret_key
    app.config["SQLALCHEMY_DATABASE_URI"] = settings.database_url
    app.config["DEBUG"] = settings.debug

    init_database(app)
    app.extensions["container"] = Container(settings)

    _configure_cors(app, settings)
    register_error_handlers(app)
    register_routes(app)

    logger.info("Aplicação inicializada (debug=%s)", settings.debug)
    return app


def _configure_cors(app, settings):
    """AP-16: allowlist de `CORS_ORIGINS` no lugar de `CORS(app)` (= `*`).
    Sem valor configurado, nenhum header CORS é emitido."""
    if not settings.cors_origins:
        logger.info("CORS desabilitado (CORS_ORIGINS não configurado)")
        return
    CORS(
        app,
        origins=settings.cors_origins,
        methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Content-Type", "Authorization"],
    )
