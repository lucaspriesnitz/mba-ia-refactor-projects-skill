'use strict';

/**
 * Encaminha rejeições de handlers async para o error handler central.
 *
 * O Express 4 não captura promise rejeitada em handler `async` -- sem isto a
 * requisição ficaria pendurada. É o equivalente moderno do `if (err) return
 * res.status(500)` repetido em cada callback do código original.
 */

const asyncHandler = (handler) => (req, res, next) => {
    Promise.resolve(handler(req, res, next)).catch(next);
};

module.exports = { asyncHandler };
