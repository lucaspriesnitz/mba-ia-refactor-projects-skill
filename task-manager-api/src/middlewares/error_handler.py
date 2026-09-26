"""Tratamento de erro central (fecha AP-14).

Antes: 11 `except:` nus -- o de `GET /tasks` (`task_routes.py:62`) engolia
qualquer bug em um 500 sem log -- e, fora dos `try`, stack trace vazando pelo
`debug=True`. Agora os controllers não têm `try/except`: erro de domínio vira o
status correspondente e qualquer outra exceção é logada com traceback e responde
mensagem genérica, sempre no formato `{'error': ...}` de antes.
"""

import logging

from flask import jsonify
from werkzeug.exceptions import HTTPException

from ..errors import DomainError

logger = logging.getLogger(__name__)

GENERIC_MESSAGE = "Erro interno"


def register_error_handlers(app):
    @app.errorhandler(DomainError)
    def handle_domain_error(error):
        logger.info("Requisição rejeitada (%s): %s", error.status_code, error.message)
        return jsonify({"error": error.message}), error.status_code

    @app.errorhandler(HTTPException)
    def handle_http_error(error):
        return jsonify({"error": error.description}), error.code or 500

    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        logger.exception("Erro não tratado: %s", error)
        return jsonify({"error": GENERIC_MESSAGE}), 500
