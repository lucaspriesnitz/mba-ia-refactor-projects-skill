"""Regra de negócio de produtos.

O controller não valida mais nada nem conhece SQL: chama estes métodos e traduz
o resultado para HTTP. Erros de domínio viram status pelo error handler central.
"""

import logging

from ..database.unit_of_work import transacao
from ..models.errors import RecursoNaoEncontrado
from ..models.serializers import serializar_produto, serializar_produtos
from ..models.validators import validar_produto

logger = logging.getLogger(__name__)


class ProdutoService:
    def __init__(self, produto_repository, provedor_conexao):
        self._produtos = produto_repository
        self._provedor_conexao = provedor_conexao

    def listar(self, limite=None, deslocamento=0):
        produtos = serializar_produtos(self._produtos.listar(limite, deslocamento))
        logger.info("Listando %s produtos", len(produtos))
        return produtos

    def buscar_por_id(self, produto_id):
        row = self._produtos.buscar_por_id(produto_id)
        if row is None:
            raise RecursoNaoEncontrado("Produto não encontrado")
        return serializar_produto(row)

    def buscar(self, termo=None, categoria=None, preco_min=None, preco_max=None,
               limite=None, deslocamento=0):
        return serializar_produtos(
            self._produtos.buscar(termo, categoria, preco_min, preco_max, limite, deslocamento)
        )

    def criar(self, dados):
        campos = validar_produto(dados)
        with transacao(self._provedor_conexao):
            produto_id = self._produtos.criar(**campos)
        logger.info("Produto criado id=%s", produto_id)
        return produto_id

    def atualizar(self, produto_id, dados):
        # A existência é checada antes da validação para preservar a precedência
        # 404 > 400 do handler original (`controllers.py:68-79`).
        if self._produtos.buscar_por_id(produto_id) is None:
            raise RecursoNaoEncontrado("Produto não encontrado")
        campos = validar_produto(dados)
        with transacao(self._provedor_conexao):
            self._produtos.atualizar(produto_id, **campos)
        logger.info("Produto atualizado id=%s", produto_id)
        return True

    def remover(self, produto_id):
        if self._produtos.buscar_por_id(produto_id) is None:
            raise RecursoNaoEncontrado("Produto não encontrado")
        with transacao(self._provedor_conexao):
            self._produtos.desativar(produto_id)
        logger.info("Produto removido id=%s", produto_id)
        return True
