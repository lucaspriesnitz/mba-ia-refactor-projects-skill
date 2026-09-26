"""Regra de negócio de pedidos -- onde ficavam os piores achados.

O que muda em relação a `models.py:133-169` e `controllers.py:188-252`:

  - **Transação com rollback** (achado HIGH): a criação inteira acontece dentro
    de uma única transação; qualquer exceção desfaz pedido, itens e estoque.
  - **Débito atômico** de estoque com guarda no WHERE e checagem de `rowcount`:
    duas requisições concorrentes não conseguem mais furar a validação e levar o
    estoque a negativo.
  - **Sem N+1**: os produtos do pedido são carregados em lote e reaproveitados;
    antes havia uma consulta por item na validação e outra na inserção.
  - **Devolução de estoque no cancelamento implementada de fato**: era um
    `print("... Devolver estoque.")` no controller (`controllers.py:250`), regra
    que nunca rodou.
  - **Notificações** saem por um colaborador injetado, não por `print` no handler.
"""

import logging

from ..database.unit_of_work import transacao
from ..models.constants import STATUS_APROVADO, STATUS_CANCELADO, STATUS_PADRAO
from ..models.errors import RegraDeNegocioViolada
from ..models.serializers import serializar_pedidos
from ..models.validators import validar_itens_de_pedido, validar_status_de_pedido

logger = logging.getLogger(__name__)


class PedidoService:
    def __init__(self, pedido_repository, produto_repository, notification_service,
                 provedor_conexao):
        self._pedidos = pedido_repository
        self._produtos = produto_repository
        self._notificacoes = notification_service
        self._provedor_conexao = provedor_conexao

    def criar(self, dados):
        campos = validar_itens_de_pedido(dados)
        usuario_id = campos["usuario_id"]
        itens = campos["itens"]

        produtos = self._produtos.buscar_muitos_por_id(
            {item["produto_id"] for item in itens}
        )
        total = self._calcular_total(itens, produtos)

        with transacao(self._provedor_conexao):
            pedido_id = self._pedidos.criar(usuario_id, STATUS_PADRAO, total)
            for item in itens:
                produto = produtos[item["produto_id"]]
                self._pedidos.adicionar_item(
                    pedido_id, item["produto_id"], item["quantidade"], produto["preco"]
                )
                debitados = self._produtos.debitar_estoque(
                    item["produto_id"], item["quantidade"]
                )
                if debitados == 0:
                    # Estoque acabou entre a validação e o débito (ou o pedido
                    # repete o mesmo produto além do disponível). A transação
                    # inteira é desfeita pelo `transacao`.
                    raise RegraDeNegocioViolada(
                        "Estoque insuficiente para " + str(produto["nome"])
                    )

        self._notificacoes.pedido_criado(pedido_id, usuario_id)
        return {"pedido_id": pedido_id, "total": total}

    def listar(self, usuario_id=None, limite=None, deslocamento=0):
        ids = self._pedidos.listar_ids(usuario_id, limite, deslocamento)
        return serializar_pedidos(self._pedidos.listar_com_itens(ids))

    def atualizar_status(self, pedido_id, dados):
        novo_status = validar_status_de_pedido(dados)

        with transacao(self._provedor_conexao):
            pedido = self._pedidos.buscar_por_id(pedido_id)
            status_anterior = pedido["status"] if pedido is not None else None

            self._pedidos.atualizar_status(pedido_id, novo_status)

            if (novo_status == STATUS_CANCELADO and status_anterior is not None
                    and status_anterior != STATUS_CANCELADO):
                self._devolver_estoque(pedido_id)

        if novo_status == STATUS_APROVADO:
            self._notificacoes.pedido_aprovado(pedido_id)
        if novo_status == STATUS_CANCELADO:
            self._notificacoes.pedido_cancelado(pedido_id)

        return True

    def _calcular_total(self, itens, produtos):
        """Regra pura: nenhum I/O, testável sem banco.

        A ordem das checagens reproduz o laço de validação original, então a
        mensagem de erro para um pedido inválido é a mesma de antes.
        """
        total = 0
        for item in itens:
            produto = produtos.get(item["produto_id"])
            if produto is None:
                raise RegraDeNegocioViolada(
                    "Produto " + str(item["produto_id"]) + " não encontrado"
                )
            if produto["estoque"] < item["quantidade"]:
                raise RegraDeNegocioViolada(
                    "Estoque insuficiente para " + str(produto["nome"])
                )
            total = total + (produto["preco"] * item["quantidade"])
        return total

    def _devolver_estoque(self, pedido_id):
        for item in self._pedidos.listar_itens(pedido_id):
            self._produtos.devolver_estoque(item["produto_id"], item["quantidade"])
        logger.info("Estoque devolvido para o pedido cancelado pedido_id=%s", pedido_id)
