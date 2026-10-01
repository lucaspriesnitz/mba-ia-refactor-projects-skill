"""Leitura da credencial `Authorization: Bearer <token>`.

A autenticação é opcional por rota -- o contrato homologado mantém as rotas
abertas -- mas, quando o header vem, ele precisa ser válido. A decisão de
*exigir* credencial para uma operação é do service (ver `UserService`).

EXCEÇÃO CRÍTICA (AP-06): rotas destrutivas (DELETE) e relatórios administrativos
exigem autenticação obrigatória. Isso prevalece sobre preservar o contrato
original da rota -- a correção do CRITICAL é mais importante que manter a rota
aberta.
"""

from functools import wraps

from flask import current_app, request

from ..errors import Forbidden, Unauthenticated

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


def requer_autenticacao(f):
    """Decorator que exige autenticação obrigatória. Retorna 401 se não houver token válido."""
    @wraps(f)
    def decorated(*args, **kwargs):
        actor = current_actor()
        if actor is None:
            raise Unauthenticated("Autenticação necessária")
        return f(*args, **kwargs)
    return decorated


def requer_admin(f):
    """Decorator que exige autenticação e papel admin. Retorna 401 se não autenticado, 403 se não admin."""
    @wraps(f)
    def decorated(*args, **kwargs):
        actor = current_actor()
        if actor is None:
            raise Unauthenticated("Autenticação necessária")
        user = current_app.extensions["container"].users.get_user(actor.user_id)
        if user is None or not user.active:
            raise Unauthenticated("Token inválido")
        if not user.is_admin:
            raise Forbidden("Apenas administradores podem acessar este recurso")
        return f(*args, **kwargs)
    return decorated
