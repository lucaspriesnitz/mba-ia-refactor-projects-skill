'use strict';

/**
 * Porta do gateway de pagamento.
 *
 * No código original a autorização era `cc.startsWith("4") ? "PAID" : "DENIED"`
 * dentro do handler HTTP (`AppManager.js:46`): não havia ponto de extensão para
 * um provedor real. Aqui a decisão vem de um colaborador injetado -- trocar o
 * fake pelo provedor real é registrar outra implementação no `container`, sem
 * tocar no service nem no controller.
 *
 * Contrato:
 *
 *   authorize({ card, amount, currency, idempotencyKey })
 *     → { status: 'PAID' | 'DENIED', authorizationId, provider }
 *
 * Regras da porta:
 *  - o número do cartão nunca é logado nem persistido (PCI-DSS);
 *  - `idempotencyKey` identifica a tentativa: o provedor deve devolver o mesmo
 *    resultado para a mesma chave, em vez de cobrar duas vezes num retry.
 */

const { randomUUID } = require('node:crypto');

/** Mascaramento para log/auditoria: só os 4 últimos dígitos sobrevivem. */
function mascararCartao(card) {
    const digitos = String(card || '').replace(/\D/g, '');
    if (digitos.length < 4) return '****';
    return `**** **** **** ${digitos.slice(-4)}`;
}

function novaChaveIdempotencia() {
    return randomUUID();
}

module.exports = { mascararCartao, novaChaveIdempotencia };
