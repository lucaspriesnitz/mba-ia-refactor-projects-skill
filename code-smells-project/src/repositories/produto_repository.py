"""Acesso a dados de produtos. 100% parametrizado (fecha AP-01).

Antes: `"SELECT * FROM produtos WHERE id = " + str(id)` (`models.py:28`), INSERT
e UPDATE por concatenação (`models.py:47-50, 57-61`) e o construtor de busca
interpolando `termo`/`categoria`/`preco_*` da querystring (`models.py:289-297`).
"""

from .base import RepositoryBase, montar_clausula_de_paginacao

COLUNAS = "id, nome, descricao, preco, estoque, categoria, ativo, criado_em"


class ProdutoRepository(RepositoryBase):
    def listar(self, limite=None, deslocamento=0):
        sufixo, parametros = montar_clausula_de_paginacao(limite, deslocamento)
        cursor = self._cursor()
        cursor.execute(
            "SELECT " + COLUNAS + " FROM produtos WHERE ativo = 1 ORDER BY id" + sufixo,
            parametros,
        )
        return cursor.fetchall()

    def buscar_por_id(self, produto_id):
        cursor = self._cursor()
        cursor.execute(
            "SELECT " + COLUNAS + " FROM produtos WHERE id = ? AND ativo = 1",
            (produto_id,),
        )
        return cursor.fetchone()

    def buscar_muitos_por_id(self, produto_ids):
        """Carregamento em lote -- evita uma query por item (AP-13)."""
        if not produto_ids:
            return {}
        marcadores = ", ".join("?" for _ in produto_ids)
        cursor = self._cursor()
        cursor.execute(
            "SELECT " + COLUNAS + " FROM produtos WHERE ativo = 1 AND id IN (" + marcadores + ")",
            list(produto_ids),
        )
        return {row["id"]: row for row in cursor.fetchall()}

    def criar(self, nome, descricao, preco, estoque, categoria):
        cursor = self._cursor()
        cursor.execute(
            "INSERT INTO produtos (nome, descricao, preco, estoque, categoria)"
            " VALUES (?, ?, ?, ?, ?)",
            (nome, descricao, preco, estoque, categoria),
        )
        return cursor.lastrowid

    def atualizar(self, produto_id, nome, descricao, preco, estoque, categoria):
        cursor = self._cursor()
        cursor.execute(
            "UPDATE produtos SET nome = ?, descricao = ?, preco = ?, estoque = ?,"
            " categoria = ? WHERE id = ? AND ativo = 1",
            (nome, descricao, preco, estoque, categoria, produto_id),
        )
        return cursor.rowcount

    def desativar(self, produto_id):
        """Soft delete: a coluna `ativo` existia no schema mas nenhuma query a
        usava, e o DELETE era físico. Como todas as leituras filtram `ativo = 1`,
        o efeito observável é o mesmo do DELETE anterior -- com a diferença de
        que pedidos antigos continuam exibindo o nome do produto."""
        cursor = self._cursor()
        cursor.execute(
            "UPDATE produtos SET ativo = 0 WHERE id = ? AND ativo = 1", (produto_id,)
        )
        return cursor.rowcount

    def buscar(self, termo=None, categoria=None, preco_min=None, preco_max=None,
               limite=None, deslocamento=0):
        condicoes = ["ativo = 1"]
        parametros = []

        if termo:
            condicoes.append("(nome LIKE ? OR descricao LIKE ?)")
            curinga = "%" + termo + "%"
            parametros.extend([curinga, curinga])
        if categoria:
            condicoes.append("categoria = ?")
            parametros.append(categoria)
        # `is not None`: antes `if preco_min:` descartava silenciosamente o zero.
        if preco_min is not None:
            condicoes.append("preco >= ?")
            parametros.append(preco_min)
        if preco_max is not None:
            condicoes.append("preco <= ?")
            parametros.append(preco_max)

        sufixo, parametros_pagina = montar_clausula_de_paginacao(limite, deslocamento)
        cursor = self._cursor()
        cursor.execute(
            "SELECT " + COLUNAS + " FROM produtos WHERE " + " AND ".join(condicoes) +
            " ORDER BY id" + sufixo,
            parametros + parametros_pagina,
        )
        return cursor.fetchall()

    def debitar_estoque(self, produto_id, quantidade):
        """Débito atômico: a guarda `estoque >= ?` está na própria cláusula WHERE.

        Antes, validar e debitar eram dois laços separados sobre uma conexão
        global compartilhada -- duas requisições concorrentes podiam passar na
        validação e levar o estoque a negativo. `rowcount == 0` significa que o
        estoque acabou entre a validação e o débito.
        """
        cursor = self._cursor()
        cursor.execute(
            "UPDATE produtos SET estoque = estoque - ? WHERE id = ? AND estoque >= ?",
            (quantidade, produto_id, quantidade),
        )
        return cursor.rowcount

    def devolver_estoque(self, produto_id, quantidade):
        cursor = self._cursor()
        cursor.execute(
            "UPDATE produtos SET estoque = estoque + ? WHERE id = ?",
            (quantidade, produto_id),
        )
        return cursor.rowcount
