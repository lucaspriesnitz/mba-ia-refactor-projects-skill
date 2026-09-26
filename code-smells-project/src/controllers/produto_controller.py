"""Controller de produtos: só HTTP.

Compare com `controllers.py:24-58`, que tinha 9 validações inline, a lista de
categorias literal e um `try/except` de função inteira. Toda essa regra saiu para
`services/produto_service.py` e `models/validators.py`.
"""

from flask import Blueprint, request

from ..models.validators import validar_preco_de_filtro
from .envelope import resposta_de_sucesso
from .suporte import container, corpo_json, parametros_de_pagina

produto_bp = Blueprint("produtos", __name__)


@produto_bp.get("/produtos")
def listar_produtos():
    limite, deslocamento = parametros_de_pagina()
    produtos = container().produto_service.listar(limite, deslocamento)
    return resposta_de_sucesso(dados=produtos)


@produto_bp.get("/produtos/busca")
def buscar_produtos():
    limite, deslocamento = parametros_de_pagina()
    resultados = container().produto_service.buscar(
        termo=request.args.get("q", ""),
        categoria=request.args.get("categoria"),
        preco_min=validar_preco_de_filtro(request.args.get("preco_min"), "preco_min"),
        preco_max=validar_preco_de_filtro(request.args.get("preco_max"), "preco_max"),
        limite=limite,
        deslocamento=deslocamento,
    )
    return resposta_de_sucesso(dados=resultados, extra={"total": len(resultados)})


@produto_bp.get("/produtos/<int:id>")
def buscar_produto(id):
    produto = container().produto_service.buscar_por_id(id)
    return resposta_de_sucesso(dados=produto)


@produto_bp.post("/produtos")
def criar_produto():
    produto_id = container().produto_service.criar(corpo_json())
    return resposta_de_sucesso(
        dados={"id": produto_id}, mensagem="Produto criado", status=201
    )


@produto_bp.put("/produtos/<int:id>")
def atualizar_produto(id):
    container().produto_service.atualizar(id, corpo_json())
    return resposta_de_sucesso(mensagem="Produto atualizado")


@produto_bp.delete("/produtos/<int:id>")
def deletar_produto(id):
    container().produto_service.remover(id)
    return resposta_de_sucesso(mensagem="Produto deletado")
