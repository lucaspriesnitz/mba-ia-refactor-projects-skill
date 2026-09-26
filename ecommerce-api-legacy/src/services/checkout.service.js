'use strict';

/**
 * Regra de negócio do checkout (T-08).
 *
 * Saiu inteira do handler HTTP (`AppManager.js:28-78`), que fazia validação,
 * busca, hashing, autorização de pagamento, três persistências e cache em 50
 * linhas aninhadas. Este service não conhece `req`/`res` e não monta SQL --
 * pode ser chamado por um job ou por um teste sem subir Express.
 */

const { ValidationError, NotFoundError, PaymentDeclinedError } = require('../models/errors');
const { novaChaveIdempotencia } = require('../gateways/paymentGateway');

class CheckoutService {
    #db;
    #users;
    #courses;
    #enrollments;
    #payments;
    #auditLogs;
    #paymentGateway;
    #passwordHasher;
    #logger;

    constructor({
        db,
        userRepository,
        courseRepository,
        enrollmentRepository,
        paymentRepository,
        auditLogRepository,
        paymentGateway,
        passwordHasher,
        logger,
    }) {
        this.#db = db;
        this.#users = userRepository;
        this.#courses = courseRepository;
        this.#enrollments = enrollmentRepository;
        this.#payments = paymentRepository;
        this.#auditLogs = auditLogRepository;
        this.#paymentGateway = paymentGateway;
        this.#passwordHasher = passwordHasher;
        this.#logger = logger;
    }

    async enroll({ name, email, password, courseId, card, idempotencyKey }) {
        this.#validar({ name, email, courseId, card });

        const curso = await this.#courses.findActiveById(courseId);
        if (!curso) throw new NotFoundError('Curso não encontrado');

        const usuarioExistente = await this.#users.findActiveByEmail(email);

        // Senha obrigatória quando a conta ainda não existe. O original criava o
        // usuário com `badCrypto(p || "123456")` (`AppManager.js:68`): senha
        // padrão previsível e idêntica para todos.
        if (!usuarioExistente && !password) {
            throw new ValidationError('Informe a senha (pwd) para criar a conta');
        }

        const chave = idempotencyKey || novaChaveIdempotencia();
        const autorizacao = await this.#paymentGateway.authorize({
            card,
            amount: curso.price,
            currency: 'BRL',
            idempotencyKey: chave,
        });

        if (autorizacao.status !== 'PAID') {
            // Recusa antes de qualquer escrita: o original já tinha criado o
            // usuário nesse ponto e deixava a linha para trás.
            throw new PaymentDeclinedError('Pagamento recusado');
        }

        const passwordHash = usuarioExistente ? null : await this.#passwordHasher.hash(password);

        // Uma única unidade de trabalho: usuário + matrícula + pagamento +
        // auditoria. Qualquer falha desfaz tudo (antes eram 3 escritas soltas,
        // `AppManager.js:50-62`).
        const resultado = await this.#db.transaction(async (tx) => {
            const usuario = usuarioExistente
                || await this.#users.create({ name, email, passwordHash }, tx);

            const matricula = await this.#enrollments.create(
                { userId: usuario.id, courseId: curso.id },
                tx
            );
            await this.#payments.create(
                { enrollmentId: matricula.id, amount: curso.price, status: autorizacao.status },
                tx
            );
            await this.#auditLogs.record(`Checkout curso ${curso.id} por ${usuario.id}`, tx);

            return { enrollmentId: matricula.id, userId: usuario.id };
        });

        this.#logger.info(
            {
                userId: resultado.userId,
                courseId: curso.id,
                enrollmentId: resultado.enrollmentId,
                authorizationId: autorizacao.authorizationId,
            },
            'Checkout concluído'
        );

        return { enrollmentId: resultado.enrollmentId };
    }

    #validar({ name, email, courseId, card }) {
        // Mesmos campos exigidos pelo original (`AppManager.js:35`), agora com
        // mensagem por campo em vez de um "Bad Request" cru.
        const faltando = [];
        if (!name) faltando.push('usr');
        if (!email) faltando.push('eml');
        if (!courseId) faltando.push('c_id');
        if (!card) faltando.push('card');

        if (faltando.length > 0) {
            throw new ValidationError(`Campos obrigatórios ausentes: ${faltando.join(', ')}`);
        }
    }
}

module.exports = { CheckoutService };
