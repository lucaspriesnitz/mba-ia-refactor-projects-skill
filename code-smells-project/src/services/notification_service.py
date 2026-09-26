"""Notificações como colaborador injetado (fecha parte de AP-10 e AP-15).

Antes, o controller disparava "e-mail/SMS/push" com `print`
(`controllers.py:208-210, 248, 250`) -- efeito colateral de negócio dentro do
ciclo HTTP, e sem nada realmente sendo enviado.

Esta implementação continua não enviando nada de fato, mas: (a) é uma fronteira
explícita para plugar um provedor real, (b) usa `logging` com nível, e (c) pode
ser chamada por um job ou uma CLI, não só por uma rota.
"""

import logging

logger = logging.getLogger(__name__)


class NotificationService:
    def pedido_criado(self, pedido_id, usuario_id):
        logger.info(
            "Notificação de pedido criado enfileirada (email/sms/push) "
            "pedido_id=%s usuario_id=%s",
            pedido_id,
            usuario_id,
        )

    def pedido_aprovado(self, pedido_id):
        logger.info("Notificação de pedido aprovado enfileirada pedido_id=%s", pedido_id)

    def pedido_cancelado(self, pedido_id):
        logger.info("Notificação de pedido cancelado enfileirada pedido_id=%s", pedido_id)
