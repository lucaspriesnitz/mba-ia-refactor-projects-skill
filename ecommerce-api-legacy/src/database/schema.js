'use strict';

/**
 * Schema versionado, fora do código de aplicação (`AppManager.js:10-23`).
 *
 * Mudanças em relação ao DDL original:
 *  - `users.pass TEXT` (senha em texto puro, AP-03) → `users.password_hash`;
 *  - `users.deleted_at` para exclusão lógica (ver `user.service.js`);
 *  - FOREIGN KEY com `ON DELETE RESTRICT` em `enrollments` e `payments`, que
 *    antes guardavam ids soltos e permitiam órfãos permanentes;
 *  - índices nas colunas usadas por lookup/JOIN.
 */

const MIGRACOES = [
    {
        versao: 1,
        nome: 'schema inicial',
        sql: `
            CREATE TABLE IF NOT EXISTS users (
                id            INTEGER PRIMARY KEY,
                name          TEXT NOT NULL,
                email         TEXT NOT NULL UNIQUE,
                password_hash TEXT,
                created_at    DATETIME NOT NULL DEFAULT (datetime('now')),
                deleted_at    DATETIME
            );

            CREATE TABLE IF NOT EXISTS courses (
                id     INTEGER PRIMARY KEY,
                title  TEXT NOT NULL,
                price  REAL NOT NULL,
                active INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS enrollments (
                id         INTEGER PRIMARY KEY,
                user_id    INTEGER NOT NULL REFERENCES users(id)   ON DELETE RESTRICT,
                course_id  INTEGER NOT NULL REFERENCES courses(id) ON DELETE RESTRICT,
                created_at DATETIME NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS payments (
                id            INTEGER PRIMARY KEY,
                enrollment_id INTEGER NOT NULL REFERENCES enrollments(id) ON DELETE RESTRICT,
                amount        REAL NOT NULL,
                status        TEXT NOT NULL,
                created_at    DATETIME NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS audit_logs (
                id         INTEGER PRIMARY KEY,
                action     TEXT NOT NULL,
                created_at DATETIME NOT NULL DEFAULT (datetime('now'))
            );

            CREATE INDEX IF NOT EXISTS idx_enrollments_course ON enrollments(course_id);
            CREATE INDEX IF NOT EXISTS idx_enrollments_user   ON enrollments(user_id);
            CREATE INDEX IF NOT EXISTS idx_payments_enrollment ON payments(enrollment_id);
        `,
    },
];

async function migrar(db, logger) {
    await db.exec('CREATE TABLE IF NOT EXISTS schema_migrations (versao INTEGER PRIMARY KEY, aplicada_em DATETIME NOT NULL DEFAULT (datetime(\'now\')))');

    for (const migracao of MIGRACOES) {
        const jaAplicada = await db.get('SELECT versao FROM schema_migrations WHERE versao = ?', [migracao.versao]);
        if (jaAplicada) continue;

        await db.exec(migracao.sql);
        await db.run('INSERT INTO schema_migrations (versao) VALUES (?)', [migracao.versao]);
        logger.info({ versao: migracao.versao, nome: migracao.nome }, 'Migração aplicada');
    }
}

module.exports = { migrar, MIGRACOES };
