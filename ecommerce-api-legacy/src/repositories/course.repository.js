'use strict';

class CourseRepository {
    #db;

    constructor(db) {
        this.#db = db;
    }

    findActiveById(id, tx) {
        return (tx || this.#db).get(
            'SELECT id, title, price FROM courses WHERE id = ? AND active = 1',
            [id]
        );
    }
}

module.exports = { CourseRepository };
