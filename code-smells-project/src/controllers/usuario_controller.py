"""Controller de usuários e login.

`GET /usuarios` e `GET /usuarios/<id>` não devolvem mais o campo `senha`
(decisão homologada na Fase 2 -- AP-03). O login passou a incluir `token` em
`dados`, campo novo e aditivo, que é a credencial exigida pelas rotas protegidas.

EXCEÇÃO CRÍTICA (AP-06): GET /usuarios e GET /usuarios/<id> agora exigem
autenticação. A correção do CRITICAL prevalece sobre preservar o contrato
original da rota.
"""

from flask import Blueprint

from ..middlewares.auth import requer_autenticacao
from .envelope import resposta_de_sucesso
from .suporte import container, corpo_json, parametros_de_pagina

usuario_bp = Blueprint("usuarios", __name__)


@usuario_bp.get("/usuarios")
@requer_autenticacao
def listar_usuarios():
    limite, deslocamento = parametros_de_pagina()
    usuarios = container().usuario_service.listar(limite, deslocamento)
    return resposta_de_sucesso(dados=usuarios)


@usuario_bp.get("/usuarios/<int:id>")
@requer_autenticacao
def buscar_usuario(id):
    usuario = container().usuario_service.buscar_por_id(id)
    return resposta_de_sucesso(dados=usuario)


@usuario_bp.post("/usuarios")
def criar_usuario():
    usuario_id = container().usuario_service.criar(corpo_json())
    return resposta_de_sucesso(dados={"id": usuario_id}, status=201)


@usuario_bp.post("/login")
def login():
    usuario = container().usuario_service.autenticar(corpo_json())
    return resposta_de_sucesso(dados=usuario, mensagem="Login OK")
