'use strict';

class PaymentRepository {
    #db;

    constructor(db) {
        this.#db = db;
    }

    async create({ enrollmentId, amount, status }, tx) {
        const { lastID } = await (tx || this.#db).run(
            'INSERT INTO payments (enrollment_id, amount, status) VALUES (?, ?, ?)',
            [enrollmentId, amount, status]
        );
        return { id: lastID, enrollmentId, amount, status };
    }
}

module.exports = { PaymentRepository };
