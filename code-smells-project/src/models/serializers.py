"""Um serializer por entidade (fecha AP-12).

Antes: o `row -> dict` de produto estava copiado 3x e o de usuario 2x em
`models.py`. E, pior, os serializers de usuario projetavam `senha` (AP-03).
Aqui a credencial simplesmente nao tem como sair: nenhum serializer publico
conhece o campo.
"""

CAMPOS_PRODUTO = (
    "id",
    "nome",
    "descricao",
    "preco",
    "estoque",
    "categoria",
    "ativo",
    "criado_em",
)

# O campo de credencial NAO aparece aqui, de proposito.
CAMPOS_USUARIO = ("id", "nome", "email", "tipo", "criado_em")

CAMPOS_USUARIO_AUTENTICADO = ("id", "nome", "email", "tipo")

CAMPOS_PEDIDO = ("id", "usuario_id", "status", "total", "criado_em")


def serializar_produto(row):
    return {campo: row[campo] for campo in CAMPOS_PRODUTO}


def serializar_produtos(rows):
    return [serializar_produto(row) for row in rows]


def serializar_usuario(row):
    return {campo: row[campo] for campo in CAMPOS_USUARIO}


def serializar_usuarios(rows):
    return [serializar_usuario(row) for row in rows]


def serializar_usuario_autenticado(row):
    return {campo: row[campo] for campo in CAMPOS_USUARIO_AUTENTICADO}


def serializar_item_de_pedido(row):
    return {
        "produto_id": row["produto_id"],
        # NULL vindo do LEFT JOIN = produto inexistente, igual ao `if prod else`
        # do codigo original.
        "produto_nome": row["produto_nome"] if row["produto_nome"] is not None else "Desconhecido",
        "quantidade": row["quantidade"],
        "preco_unitario": row["preco_unitario"],
    }


def serializar_pedidos(rows):
    """Agrupa o resultado de uma unica query com JOIN em pedidos + itens.

    Substitui o N+2 de `models.py:187-193, 219-225`, preservando o formato
    exato do payload (inclusive a ordem dos pedidos e dos itens).
    """
    pedidos = []
    por_id = {}
    for row in rows:
        pedido = por_id.get(row["id"])
        if pedido is None:
            pedido = {campo: row[campo] for campo in CAMPOS_PEDIDO}
            pedido["itens"] = []
            por_id[row["id"]] = pedido
            pedidos.append(pedido)
        if row["produto_id"] is not None:
            pedido["itens"].append(serializar_item_de_pedido(row))
    return pedidos
