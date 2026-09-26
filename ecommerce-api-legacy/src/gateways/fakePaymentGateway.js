'use strict';

/**
 * Implementação fake da porta de pagamento.
 *
 * Mantém deliberadamente a mesma heurística do código original (cartão iniciado
 * em "4" aprova, qualquer outro recusa) para preservar o comportamento dos
 * endpoints -- é o que os cenários de `api.http` exercitam. O que mudou:
 *  - o PAN não é mais logado (`AppManager.js:45` era o vazamento CRITICAL);
 *  - a chave do gateway fica em `config`, vinda do ambiente, e nunca sai em log;
 *  - o resultado é um objeto de resposta do provedor, não um literal decidido
 *    pelo controller.
 *
 * NÃO é um gateway de verdade: não valida Luhn, validade ou CVV, e não faz
 * chamada externa. Trocá-lo por um provedor real é implementar a mesma
 * interface.
 */

const { mascararCartao } = require('./paymentGateway');

class FakePaymentGateway {
    #apiKey;
    #logger;

    constructor({ apiKey, logger }) {
        this.#apiKey = apiKey;
        this.#logger = logger;
    }

    async authorize({ card, amount, currency = 'BRL', idempotencyKey }) {
        const aprovado = String(card).startsWith('4');
        const resposta = {
            status: aprovado ? 'PAID' : 'DENIED',
            authorizationId: `fake_${idempotencyKey}`,
            provider: 'fake',
        };

        // Log de rastro sem dado sensível: 4 últimos dígitos e a chave da tentativa.
        this.#logger.info(
            {
                cartao: mascararCartao(card),
                amount,
                currency,
                idempotencyKey,
                status: resposta.status,
                // Só um indicador de que a chave está carregada -- nunca o valor.
                gatewayKeyConfigurada: Boolean(this.#apiKey),
            },
            'Autorização de pagamento processada'
        );

        return resposta;
    }
}

module.exports = { FakePaymentGateway };
