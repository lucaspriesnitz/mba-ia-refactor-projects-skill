"""Leitura da credencial `Authorization: Bearer <token>`.

A autenticação é opcional por rota -- o contrato homologado mantém as rotas
abertas -- mas, quando o header vem, ele precisa ser válido. A decisão de
*exigir* credencial para uma operação é do service (ver `UserService`).
"""

from flask import current_app, request

from ..errors import Unauthenticated

BEARER_PREFIX = "Bearer "


def current_actor():
    """`Actor` do token, `None` se não houver header; 401 se o token for inválido."""
    header = request.headers.get("Authorization")
    if not header:
        return None
    if not header.startswith(BEARER_PREFIX) or not header[len(BEARER_PREFIX):].strip():
        raise Unauthenticated("Token inválido")
    token = header[len(BEARER_PREFIX):].strip()
    return current_app.extensions["container"].tokens.decode(token)
