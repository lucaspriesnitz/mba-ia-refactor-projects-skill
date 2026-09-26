'use strict';

class UserController {
    #userService;

    constructor({ userService }) {
        this.#userService = userService;
        this.remove = this.remove.bind(this);
    }

    async remove(req, res) {
        await this.#userService.delete(req.params.id);
        // 204: a resposta original era um texto confessando um defeito que já
        // não existe (`AppManager.js:135`).
        res.status(204).end();
    }
}

module.exports = { UserController };
