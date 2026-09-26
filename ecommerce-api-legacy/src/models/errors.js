'use strict';

/**
 * Erros de domínio com código e status HTTP.
 *
 * As camadas de baixo lançam estes erros; o `errorHandler` central (AP-14)
 * é o único lugar que os traduz em resposta HTTP. Nenhum service ou repository
 * conhece `res`.
 */

class AppError extends Error {
    constructor(mensagem, { code, status }) {
        super(mensagem);
        this.name = new.target.name;
        this.code = code;
        this.status = status;
        this.esperado = true;
    }
}

class ValidationError extends AppError {
    constructor(mensagem = 'Requisição inválida') {
        super(mensagem, { code: 'VALIDATION_ERROR', status: 400 });
    }
}

class NotFoundError extends AppError {
    constructor(mensagem = 'Recurso não encontrado') {
        super(mensagem, { code: 'NOT_FOUND', status: 404 });
    }
}

class UnauthorizedError extends AppError {
    constructor(mensagem = 'Credencial ausente ou inválida') {
        super(mensagem, { code: 'UNAUTHORIZED', status: 401 });
    }
}

class PaymentDeclinedError extends AppError {
    constructor(mensagem = 'Pagamento recusado') {
        super(mensagem, { code: 'PAYMENT_DECLINED', status: 400 });
    }
}

class ConflictError extends AppError {
    constructor(mensagem = 'Conflito de estado') {
        super(mensagem, { code: 'CONFLICT', status: 409 });
    }
}

module.exports = {
    AppError,
    ValidationError,
    NotFoundError,
    UnauthorizedError,
    PaymentDeclinedError,
    ConflictError,
};
