'use strict';

/**
 * Consulta agregada do relatório financeiro (AP-13).
 *
 * O original disparava `1 + C + 2·M` queries (`AppManager.js:83-106`) -- mais de
 * 20 000 round-trips sequenciais num cenário de 50 cursos e 10 000 matrículas.
 * Aqui é **uma** consulta, com `ORDER BY` explícito para tornar a ordem do
 * relatório determinística (antes ela dependia de qual callback terminava
 * primeiro, `AppManager.js:96, 119`).
 *
 * O `LEFT JOIN` em `payments` casa apenas o pagamento de menor id por matrícula,
 * reproduzindo o `db.get` do original (que pegava o primeiro) em vez de
 * multiplicar linhas quando houver mais de um pagamento.
 */

const SQL_RELATORIO = `
    SELECT
        c.id          AS course_id,
        c.title       AS course_title,
        e.id          AS enrollment_id,
        u.name        AS student_name,
        p.amount      AS payment_amount,
        p.status      AS payment_status
    FROM courses c
    LEFT JOIN enrollments e ON e.course_id = c.id
    LEFT JOIN users u       ON u.id = e.user_id
    LEFT JOIN payments p    ON p.id = (
        SELECT MIN(id) FROM payments WHERE enrollment_id = e.id
    )
    ORDER BY c.id, e.id
`;

class ReportRepository {
    #db;

    constructor(db) {
        this.#db = db;
    }

    listCourseRevenueRows() {
        return this.#db.all(SQL_RELATORIO);
    }
}

module.exports = { ReportRepository, SQL_RELATORIO };
