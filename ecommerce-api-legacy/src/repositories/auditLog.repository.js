'use strict';

class AuditLogRepository {
    #db;

    constructor(db) {
        this.#db = db;
    }

    /**
     * Registra a ação. Participa da mesma transação da operação auditada: ou
     * tudo é gravado, ou nada -- o original respondia 200 mesmo quando este
     * INSERT falhava (`AppManager.js:57`), deixando buraco silencioso na trilha.
     */
    async record(action, tx) {
        const { lastID } = await (tx || this.#db).run(
            "INSERT INTO audit_logs (action, created_at) VALUES (?, datetime('now'))",
            [action]
        );
        return { id: lastID, action };
    }
}

module.exports = { AuditLogRepository };
