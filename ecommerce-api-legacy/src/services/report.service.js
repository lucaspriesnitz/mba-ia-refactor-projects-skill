'use strict';

/**
 * Monta o relatório financeiro a partir das linhas da consulta agregada.
 *
 * Formato de saída idêntico ao original: `[{ course, revenue, students: [{ student, paid }] }]`.
 * A diferença é que a agregação acontece em memória sobre uma única consulta,
 * sem os contadores `coursesPending`/`enrPending` compartilhados entre callbacks.
 */

class ReportService {
    #reports;

    constructor({ reportRepository }) {
        this.#reports = reportRepository;
    }

    async financialReport() {
        const linhas = await this.#reports.listCourseRevenueRows();

        const porCurso = new Map();

        for (const linha of linhas) {
            if (!porCurso.has(linha.course_id)) {
                porCurso.set(linha.course_id, { course: linha.course_title, revenue: 0, students: [] });
            }
            const curso = porCurso.get(linha.course_id);

            // Curso sem matrícula vem do LEFT JOIN com enrollment_id nulo.
            if (linha.enrollment_id === null) continue;

            if (linha.payment_status === 'PAID') {
                curso.revenue += linha.payment_amount;
            }

            curso.students.push({
                student: linha.student_name || 'Unknown',
                paid: linha.payment_amount === null ? 0 : linha.payment_amount,
            });
        }

        return [...porCurso.values()];
    }
}

module.exports = { ReportService };
