'use strict';

/**
 * Acesso a dados de `users`. Nenhuma camada acima conhece SQL (T-09).
 *
 * Todo método aceita um executor opcional (`tx`) para participar de uma
 * transação aberta pelo service.
 */

class UserRepository {
    #db;

    constructor(db) {
        this.#db = db;
    }

    #exec(tx) {
        return tx || this.#db;
    }

    findActiveByEmail(email, tx) {
        return this.#exec(tx).get(
            'SELECT id, name, email, password_hash FROM users WHERE email = ? AND deleted_at IS NULL',
            [email]
        );
    }

    findById(id, tx) {
        return this.#exec(tx).get(
            'SELECT id, name, email, deleted_at FROM users WHERE id = ?',
            [id]
        );
    }

    async create({ name, email, passwordHash }, tx) {
        const { lastID } = await this.#exec(tx).run(
            'INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)',
            [name, email, passwordHash]
        );
        return { id: lastID, name, email };
    }

    /**
     * Exclusão lógica com anonimização.
     *
     * O `DELETE FROM users` original (`AppManager.js:133`) deixava matrículas e
     * pagamentos órfãos -- a própria resposta admitia isso. Anonimizar preserva
     * a integridade financeira (a receita continua atribuída à matrícula) e
     * remove o dado pessoal, que é o objetivo real da exclusão.
     */
    async anonymize(id, tx) {
        const { changes } = await this.#exec(tx).run(
            `UPDATE users
                SET name = 'Usuário removido',
                    email = 'deleted+' || id || '@invalid.local',
                    password_hash = NULL,
                    deleted_at = datetime('now')
              WHERE id = ? AND deleted_at IS NULL`,
            [id]
        );
        return changes > 0;
    }
}

module.exports = { UserRepository };
