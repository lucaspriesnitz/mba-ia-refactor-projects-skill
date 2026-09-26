'use strict';

/**
 * Controller do checkout: traduz HTTP ↔ domínio e nada mais.
 *
 * O corpo continua aceitando os nomes crípticos originais (`usr`, `eml`, `pwd`,
 * `c_id`, `card`) para não quebrar clientes; os nomes legíveis (`name`, `email`,
 * `password`, `courseId`) são aceitos como alias, caminho de migração do
 * contrato sem versionar a rota.
 */

class CheckoutController {
    #checkoutService;

    constructor({ checkoutService }) {
        this.#checkoutService = checkoutService;
        this.create = this.create.bind(this);
    }

    async create(req, res) {
        const body = req.body || {};

        const { enrollmentId } = await this.#checkoutService.enroll({
            name: body.usr ?? body.name,
            email: body.eml ?? body.email,
            password: body.pwd ?? body.password,
            courseId: body.c_id ?? body.courseId,
            card: body.card,
            idempotencyKey: req.get('Idempotency-Key') || undefined,
        });

        res.status(200).json({ msg: 'Sucesso', enrollment_id: enrollmentId });
    }
}

module.exports = { CheckoutController };
