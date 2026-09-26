'use strict';

/**
 * Seeds de desenvolvimento -- os mesmos dados de `AppManager.js:18-21`.
 *
 * Diferenças: rodam só quando `SEED_ENABLED` está ligado (default: fora de
 * produção), são idempotentes (banco agora é persistente) e a senha passa pelo
 * mesmo caminho de hash da aplicação, nunca pelo literal `'123'` (AP-03).
 */

async function semear(db, { passwordHasher, seedPassword, logger }) {
    const { total } = await db.get('SELECT COUNT(*) AS total FROM courses');
    if (total > 0) {
        logger.debug('Seeds ignorados: banco já populado');
        return;
    }

    const hash = await passwordHasher.hash(seedPassword);

    await db.transaction(async (tx) => {
        const usuario = await tx.run(
            'INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)',
            ['Leonan', 'leonan@fullcycle.com.br', hash]
        );
        const curso = await tx.run('INSERT INTO courses (title, price, active) VALUES (?, ?, 1)', ['Clean Architecture', 997.0]);
        await tx.run('INSERT INTO courses (title, price, active) VALUES (?, ?, 1)', ['Docker', 497.0]);

        const matricula = await tx.run(
            'INSERT INTO enrollments (user_id, course_id) VALUES (?, ?)',
            [usuario.lastID, curso.lastID]
        );
        await tx.run(
            'INSERT INTO payments (enrollment_id, amount, status) VALUES (?, ?, ?)',
            [matricula.lastID, 997.0, 'PAID']
        );
    });

    logger.info('Seeds de desenvolvimento aplicados');
}

module.exports = { semear };
