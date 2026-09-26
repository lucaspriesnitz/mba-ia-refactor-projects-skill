'use strict';

/**
 * Registro de rotas → controllers. Nenhuma regra de negócio aqui.
 *
 * Os três caminhos e métodos originais estão preservados:
 *   POST   /api/checkout
 *   GET    /api/admin/financial-report   (agora exige credencial de admin)
 *   DELETE /api/users/:id                (agora exige credencial de admin)
 */

const { Router } = require('express');

const { asyncHandler } = require('../middlewares/asyncHandler');
const { criarRequerAdmin } = require('../middlewares/auth');

function criarRoutes({ config, checkoutController, reportController, userController }) {
    const router = Router();
    const requerAdmin = criarRequerAdmin(config);

    router.post('/api/checkout', asyncHandler(checkoutController.create));

    router.get(
        '/api/admin/financial-report',
        requerAdmin,
        asyncHandler(reportController.financial)
    );

    router.delete('/api/users/:id', requerAdmin, asyncHandler(userController.remove));

    return router;
}

module.exports = { criarRoutes };
