"""Acesso a dados de pedidos.

O ponto central aqui é `listar_com_itens`: substitui o N+2 de
`models.py:187-193` e `models.py:219-225` (uma query de itens por pedido e uma
query de nome por item) por duas queries de custo fixo -- a página de pedidos e
um único JOIN com itens e produtos.
"""

from .base import RepositoryBase, montar_clausula_de_paginacao

COLUNAS = "id, usuario_id, status, total, criado_em"


class PedidoRepository(RepositoryBase):
    def criar(self, usuario_id, status, total):
        cursor = self._cursor()
        cursor.execute(
            "INSERT INTO pedidos (usuario_id, status, total) VALUES (?, ?, ?)",
            (usuario_id, status, total),
        )
        return cursor.lastrowid

    def adicionar_item(self, pedido_id, produto_id, quantidade, preco_unitario):
        cursor = self._cursor()
        cursor.execute(
            "INSERT INTO itens_pedido (pedido_id, produto_id, quantidade, preco_unitario)"
            " VALUES (?, ?, ?, ?)",
            (pedido_id, produto_id, quantidade, preco_unitario),
        )
        return cursor.lastrowid

    def buscar_por_id(self, pedido_id):
        cursor = self._cursor()
        cursor.execute(
            "SELECT " + COLUNAS + " FROM pedidos WHERE id = ?", (pedido_id,)
        )
        return cursor.fetchone()

    def listar_itens(self, pedido_id):
        cursor = self._cursor()
        cursor.execute(
            "SELECT produto_id, quantidade, preco_unitario FROM itens_pedido"
            " WHERE pedido_id = ? ORDER BY id",
            (pedido_id,),
        )
        return cursor.fetchall()

    def listar_ids(self, usuario_id=None, limite=None, deslocamento=0):
        condicao = ""
        parametros = []
        if usuario_id is not None:
            condicao = " WHERE usuario_id = ?"
            parametros.append(usuario_id)
        sufixo, parametros_pagina = montar_clausula_de_paginacao(limite, deslocamento)
        cursor = self._cursor()
        cursor.execute(
            "SELECT id FROM pedidos" + condicao + " ORDER BY id" + sufixo,
            parametros + parametros_pagina,
        )
        return [row["id"] for row in cursor.fetchall()]

    def listar_com_itens(self, pedido_ids):
        """Um JOIN só para todos os pedidos da página, itens e nomes de produto."""
        if not pedido_ids:
            return []
        marcadores = ", ".join("?" for _ in pedido_ids)
        cursor = self._cursor()
        cursor.execute(
            "SELECT p.id, p.usuario_id, p.status, p.total, p.criado_em,"
            "       i.produto_id, i.quantidade, i.preco_unitario,"
            "       pr.nome AS produto_nome"
            "  FROM pedidos p"
            "  LEFT JOIN itens_pedido i ON i.pedido_id = p.id"
            "  LEFT JOIN produtos pr ON pr.id = i.produto_id"
            " WHERE p.id IN (" + marcadores + ")"
            " ORDER BY p.id, i.id",
            list(pedido_ids),
        )
        return cursor.fetchall()

    def atualizar_status(self, pedido_id, novo_status):
        cursor = self._cursor()
        cursor.execute(
            "UPDATE pedidos SET status = ? WHERE id = ?", (novo_status, pedido_id)
        )
        return cursor.rowcount
