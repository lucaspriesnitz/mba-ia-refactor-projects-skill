'use strict';

/**
 * Logger estruturado com nível e redação de campos sensíveis (AP-15).
 *
 * Substitui os três `console.log` do código original -- incluindo o de
 * `AppManager.js:45`, que imprimia o PAN completo e a chave live do gateway.
 * Os `redact` abaixo são a rede de segurança: mesmo que alguém logue um objeto
 * com `card`/`password`/`authorization`, o valor sai como `[Redacted]`.
 */

const pino = require('pino');

const CAMPOS_REDIGIDOS = [
    'card',
    'cc',
    'password',
    'pwd',
    'pass',
    'password_hash',
    'apiKey',
    'paymentGatewayKey',
    'authorization',
    '*.card',
    '*.password',
    'req.headers.authorization',
    'req.body.card',
    'req.body.pwd',
];

function criarLogger(config) {
    return pino({
        level: config.logLevel,
        base: { service: 'ecommerce-api' },
        redact: { paths: CAMPOS_REDIGIDOS, censor: '[Redacted]' },
    });
}

module.exports = { criarLogger };
