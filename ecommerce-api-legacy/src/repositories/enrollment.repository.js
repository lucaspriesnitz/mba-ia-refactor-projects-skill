'use strict';

class EnrollmentRepository {
    #db;

    constructor(db) {
        this.#db = db;
    }

    async create({ userId, courseId }, tx) {
        const { lastID } = await (tx || this.#db).run(
            'INSERT INTO enrollments (user_id, course_id) VALUES (?, ?)',
            [userId, courseId]
        );
        return { id: lastID, userId, courseId };
    }
}

module.exports = { EnrollmentRepository };
