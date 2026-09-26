'use strict';

/**
 * Tratamento de erro central (AP-14 / T-12) e handler de rota inexistente.
 *
 * Único ponto que traduz erro em resposta HTTP. Erros de domínio viram o status
 * e o código que declaram; qualquer outra coisa é 500 com mensagem genérica e
 * stack registrado no log interno — nunca no corpo da resposta.
 */

const { AppError } = require('../models/errors');

function notFoundHandler(req, res) {
    res.status(404).json({
        error: { code: 'ROUTE_NOT_FOUND', message: `Rota não encontrada: ${req.method} ${req.originalUrl}` },
    });
}

function criarErrorHandler(logger) {
    // A assinatura de 4 argumentos é o que marca o middleware como error handler.
    return function errorHandler(err, req, res, next) {
        if (res.headersSent) return next(err);

        // Corpo JSON malformado: sem isto o handler padrão do Express devolve
        // caminhos internos do servidor.
        if (err instanceof SyntaxError && 'body' in err) {
            return res.status(400).json({
                error: { code: 'INVALID_JSON', message: 'Corpo da requisição não é um JSON válido' },
            });
        }

        if (err instanceof AppError) {
            logger.warn(
                { code: err.code, status: err.status, path: req.originalUrl, method: req.method },
                err.message
            );
            return res.status(err.status).json({ error: { code: err.code, message: err.message } });
        }

        logger.error(
            { err, path: req.originalUrl, method: req.method },
            'Erro não tratado'
        );
        return res.status(500).json({
            error: { code: 'INTERNAL_ERROR', message: 'Erro interno' },
        });
    };
}

module.exports = { criarErrorHandler, notFoundHandler };
