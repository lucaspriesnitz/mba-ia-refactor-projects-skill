"""Validação de entrada na borda, com marshmallow.

Antes cada handler repetia `if not data: return 400` (e `PUT /categories/<id>`
esquecia, `report_routes.py:196-197`) e comparava tipos crus -- `priority: "alta"`
virava 500. Agora todo corpo passa por `load_input`, que devolve o dado já
coerido ou levanta `InvalidInput` com a primeira mensagem, na ordem de
declaração dos campos, no mesmo formato `{'error': ...}` de antes.
"""

from marshmallow import ValidationError

from ..errors import InvalidInput

INVALID_BODY = "Dados inválidos"


def load_input(schema, data):
    if not isinstance(data, dict) or not data:
        raise InvalidInput(INVALID_BODY)
    try:
        return schema.load(data)
    except ValidationError as error:
        raise InvalidInput(_first_message(schema, error.messages))


def _first_message(schema, messages):
    for field_name in schema.fields:
        if field_name in messages:
            return _flatten(messages[field_name])
    return INVALID_BODY


def _flatten(message):
    while isinstance(message, (list, dict)):
        message = next(iter(message.values())) if isinstance(message, dict) else message[0]
    return message
