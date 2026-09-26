"""Controller de pedidos.

Os efeitos colaterais de negócio que estavam aqui -- notificações
(`controllers.py:208-210`) e a decisão por status, incluindo a devolução de
estoque que nunca foi implementada (`controllers.py:247-250`) -- foram para
`services/pedido_service.py`.
"""

from flask import Blueprint

from .envelope import resposta_de_sucesso
from .suporte import container, corpo_json, parametros_de_pagina

pedido_bp = Blueprint("pedidos", __name__)


@pedido_bp.post("/pedidos")
def criar_pedido():
    resultado = container().pedido_service.criar(corpo_json())
    return resposta_de_sucesso(
        dados=resultado, mensagem="Pedido criado com sucesso", status=201
    )


@pedido_bp.get("/pedidos")
def listar_todos_pedidos():
    limite, deslocamento = parametros_de_pagina()
    pedidos = container().pedido_service.listar(limite=limite, deslocamento=deslocamento)
    return resposta_de_sucesso(dados=pedidos)


@pedido_bp.get("/pedidos/usuario/<int:usuario_id>")
def listar_pedidos_usuario(usuario_id):
    limite, deslocamento = parametros_de_pagina()
    pedidos = container().pedido_service.listar(
        usuario_id=usuario_id, limite=limite, deslocamento=deslocamento
    )
    return resposta_de_sucesso(dados=pedidos)


@pedido_bp.put("/pedidos/<int:pedido_id>/status")
def atualizar_status_pedido(pedido_id):
    container().pedido_service.atualizar_status(pedido_id, corpo_json())
    return resposta_de_sucesso(mensagem="Status atualizado")
