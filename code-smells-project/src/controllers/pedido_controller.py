"""Controller de pedidos.

Os efeitos colaterais de negócio que estavam aqui -- notificações
(`controllers.py:208-210`) e a decisão por status, incluindo a devolução de
estoque que nunca foi implementada (`controllers.py:247-250`) -- foram para
`services/pedido_service.py`.

EXCEÇÃO CRÍTICA (AP-06): as quatro rotas de pedido exigem autenticação. A correção
do CRITICAL prevalece sobre preservar o contrato original da rota.

`GET /pedidos` exige papel `admin`: a lista de todos os pedidos é o dado bruto que
compõe `GET /relatorios/vendas`, já admin-only -- deixar as linhas abertas enquanto o
agregado é fechado não protege nada. `GET /pedidos/usuario/<id>` exige credencial e
**posse**: cada um vê o próprio histórico, admin vê o de qualquer um. Sem a checagem
de posse a rota seria enumeração do histórico de compra por id.
"""

from flask import Blueprint

from ..middlewares.auth import requer_autenticacao, requer_papel, usuario_autenticado
from ..models.errors import NaoAutorizado
from .envelope import resposta_de_sucesso
from .suporte import container, corpo_json, parametros_de_pagina

pedido_bp = Blueprint("pedidos", __name__)

PAPEL_ADMIN = "admin"


@pedido_bp.post("/pedidos")
@requer_autenticacao
def criar_pedido():
    resultado = container().pedido_service.criar(corpo_json())
    return resposta_de_sucesso(
        dados=resultado, mensagem="Pedido criado com sucesso", status=201
    )


@pedido_bp.get("/pedidos")
@requer_papel(PAPEL_ADMIN)
def listar_todos_pedidos():
    limite, deslocamento = parametros_de_pagina()
    pedidos = container().pedido_service.listar(limite=limite, deslocamento=deslocamento)
    return resposta_de_sucesso(dados=pedidos)


@pedido_bp.get("/pedidos/usuario/<int:usuario_id>")
@requer_autenticacao
def listar_pedidos_usuario(usuario_id):
    portador = usuario_autenticado() or {}
    if portador.get("papel") != PAPEL_ADMIN and portador.get("sub") != usuario_id:
        raise NaoAutorizado("Permissão insuficiente")

    limite, deslocamento = parametros_de_pagina()
    pedidos = container().pedido_service.listar(
        usuario_id=usuario_id, limite=limite, deslocamento=deslocamento
    )
    return resposta_de_sucesso(dados=pedidos)


@pedido_bp.put("/pedidos/<int:pedido_id>/status")
@requer_papel("admin")
def atualizar_status_pedido(pedido_id):
    container().pedido_service.atualizar_status(pedido_id, corpo_json())
    return resposta_de_sucesso(mensagem="Status atualizado")
