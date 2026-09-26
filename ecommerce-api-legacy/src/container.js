'use strict';

/**
 * Composition root: o único lugar que sabe qual implementação concreta cada
 * camada recebe. Substitui o `new AppManager()` que instanciava banco, rotas e
 * regra de negócio no próprio construtor (`AppManager.js:5-8`).
 */

const { Database } = require('./database/connection');
const { migrar } = require('./database/schema');
const { semear } = require('./database/seed');

const passwordHasher = require('./security/passwordHasher');
const { FakePaymentGateway } = require('./gateways/fakePaymentGateway');

const { UserRepository } = require('./repositories/user.repository');
const { CourseRepository } = require('./repositories/course.repository');
const { EnrollmentRepository } = require('./repositories/enrollment.repository');
const { PaymentRepository } = require('./repositories/payment.repository');
const { AuditLogRepository } = require('./repositories/auditLog.repository');
const { ReportRepository } = require('./repositories/report.repository');

const { CheckoutService } = require('./services/checkout.service');
const { ReportService } = require('./services/report.service');
const { UserService } = require('./services/user.service');

const { CheckoutController } = require('./controllers/checkout.controller');
const { ReportController } = require('./controllers/report.controller');
const { UserController } = require('./controllers/user.controller');

const GATEWAYS = {
    fake: FakePaymentGateway,
};

function criarPaymentGateway(config, logger) {
    const Gateway = GATEWAYS[config.payment.driver];
    if (!Gateway) {
        throw new Error(
            `PAYMENT_GATEWAY_DRIVER desconhecido: ${config.payment.driver}. ` +
            `Disponíveis: ${Object.keys(GATEWAYS).join(', ')}`
        );
    }
    return new Gateway({ apiKey: config.payment.apiKey, logger });
}

async function criarContainer(config, logger) {
    const db = await Database.abrir({ dbPath: config.dbPath, verbose: config.dbVerbose }, logger);
    await migrar(db, logger);

    if (config.seedEnabled) {
        await semear(db, { passwordHasher, seedPassword: config.seedPassword, logger });
    }

    const userRepository = new UserRepository(db);
    const courseRepository = new CourseRepository(db);
    const enrollmentRepository = new EnrollmentRepository(db);
    const paymentRepository = new PaymentRepository(db);
    const auditLogRepository = new AuditLogRepository(db);
    const reportRepository = new ReportRepository(db);

    const paymentGateway = criarPaymentGateway(config, logger);

    const checkoutService = new CheckoutService({
        db,
        userRepository,
        courseRepository,
        enrollmentRepository,
        paymentRepository,
        auditLogRepository,
        paymentGateway,
        passwordHasher,
        logger,
    });
    const reportService = new ReportService({ reportRepository });
    const userService = new UserService({ db, userRepository, auditLogRepository, logger });

    return {
        config,
        logger,
        db,
        checkoutController: new CheckoutController({ checkoutService }),
        reportController: new ReportController({ reportService }),
        userController: new UserController({ userService }),
    };
}

module.exports = { criarContainer };
