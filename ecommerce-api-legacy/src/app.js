'use strict';

/**
 * Fábrica da aplicação Express: monta middlewares, rotas e tratamento de erro.
 *
 * Não abre conexão, não lê ambiente e não chama `listen` — isso é do
 * `container` e do `server`. Assim a app é instanciável num teste com
 * dependências de mentira.
 */

const express = require('express');

const { criarRoutes } = require('./routes');
const { criarErrorHandler, notFoundHandler } = require('./middlewares/errorHandler');

function criarApp(container) {
    const app = express();

    app.disable('x-powered-by');
    app.use(express.json({ limit: '100kb' }));

    app.get('/health', (req, res) => res.json({ status: 'ok' }));

    app.use(criarRoutes(container));

    app.use(notFoundHandler);
    app.use(criarErrorHandler(container.logger));

    return app;
}

module.exports = { criarApp };
