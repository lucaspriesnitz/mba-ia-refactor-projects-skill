'use strict';

/**
 * Regra de exclusão de usuário.
 *
 * O original apagava a linha e respondia 200 com
 * "Usuário deletado, mas as matrículas e pagamentos ficaram sujos no banco."
 * -- inclusive quando o DELETE falhava (`AppManager.js:133-135`).
 *
 * Aqui a exclusão é lógica + anonimização, dentro de transação e auditada:
 * o dado pessoal some, a matrícula e o pagamento continuam íntegros (o
 * relatório financeiro não perde receita nem ganha órfão).
 */

const { NotFoundError, ValidationError } = require('../models/errors');

class UserService {
    #db;
    #users;
    #auditLogs;
    #logger;

    constructor({ db, userRepository, auditLogRepository, logger }) {
        this.#db = db;
        this.#users = userRepository;
        this.#auditLogs = auditLogRepository;
        this.#logger = logger;
    }

    async delete(rawId) {
        const id = Number.parseInt(rawId, 10);
        if (!Number.isInteger(id) || id <= 0) {
            throw new ValidationError('Id de usuário inválido');
        }

        const usuario = await this.#users.findById(id);
        if (!usuario) throw new NotFoundError('Usuário não encontrado');

        await this.#db.transaction(async (tx) => {
            const anonimizado = await this.#users.anonymize(id, tx);
            // Já anonimizado antes: operação idempotente, sem novo registro.
            if (anonimizado) {
                await this.#auditLogs.record(`Exclusão do usuário ${id}`, tx);
            }
        });

        this.#logger.info({ userId: id }, 'Usuário anonimizado');
    }
}

module.exports = { UserService };
