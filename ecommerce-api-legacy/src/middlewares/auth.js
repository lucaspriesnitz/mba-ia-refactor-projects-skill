'use strict';

/**
 * Autenticação das rotas sensíveis (AP-06 / T-05).
 *
 * Antes não existia mecanismo algum: `GET /api/admin/financial-report` expunha
 * receita e a lista nominal de alunos, e `DELETE /api/users/:id` apagava
 * qualquer usuário — ambos para requisição anônima.
 *
 * O esquema aqui é um token administrativo estático vindo do ambiente
 * (`ADMIN_API_TOKEN`), enviado como `Authorization: Bearer <token>`. É o mínimo
 * defensável para uma API que não tem cadastro de credencial nem endpoint de
 * login; a evolução natural (registrada no README) é emitir token por usuário
 * com papel. A comparação é em tempo constante para não vazar o token por
 * timing.
 */

const { timingSafeEqual } = require('node:crypto');

const { UnauthorizedError } = require('../models/errors');

const PREFIXO_BEARER = 'Bearer ';

function comparaSegura(a, b) {
    const bufferA = Buffer.from(a, 'utf8');
    const bufferB = Buffer.from(b, 'utf8');
    if (bufferA.length !== bufferB.length) return false;
    return timingSafeEqual(bufferA, bufferB);
}

function criarRequerAdmin(config) {
    return function requerAdmin(req, res, next) {
        const cabecalho = req.get('Authorization') || '';
        if (!cabecalho.startsWith(PREFIXO_BEARER)) {
            return next(new UnauthorizedError('Credencial ausente'));
        }

        const token = cabecalho.slice(PREFIXO_BEARER.length).trim();
        if (!token || !comparaSegura(token, config.adminApiToken)) {
            return next(new UnauthorizedError('Credencial inválida'));
        }

        req.auth = { role: 'admin' };
        return next();
    };
}

module.exports = { criarRequerAdmin };
