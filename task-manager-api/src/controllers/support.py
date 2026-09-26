"""Utilitários HTTP compartilhados pelos controllers."""

from flask import current_app, jsonify, request

from ..errors import InvalidInput
from ..repositories import Page

TOTAL_COUNT_HEADER = "X-Total-Count"


def container():
    return current_app.extensions["container"]


def json_body():
    return request.get_json(silent=True)


def optional_int_arg(name):
    """Query string inteira opcional. Antes `int(priority)` em
    `task_routes.py:261,264` virava 500 com `?priority=abc`."""
    value = request.args.get(name, "")
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        raise InvalidInput(f"Parâmetro {name} inválido")


def page_from_request():
    """`?limit=&offset=` opcionais. Sem `limit`, vale `LIST_DEFAULT_LIMIT`
    (vazio = sem limite, contrato original); nunca acima de `LIST_MAX_LIMIT`."""
    settings = container().settings
    limit = optional_int_arg("limit")
    offset = optional_int_arg("offset") or 0
    if limit is not None and limit < 1:
        raise InvalidInput("Parâmetro limit inválido")
    if offset < 0:
        raise InvalidInput("Parâmetro offset inválido")
    if limit is None:
        limit = settings.list_default_limit
    if limit is not None:
        limit = min(limit, settings.list_max_limit)
    return Page(limit=limit, offset=offset)


def paginated_response(items, total):
    """Corpo continua sendo a lista pura; o total vai em header (aditivo)."""
    response = jsonify(items)
    response.headers[TOTAL_COUNT_HEADER] = str(total)
    return response, 200
