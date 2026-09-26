'use strict';

class ReportController {
    #reportService;

    constructor({ reportService }) {
        this.#reportService = reportService;
        this.financial = this.financial.bind(this);
    }

    async financial(req, res) {
        res.json(await this.#reportService.financialReport());
    }
}

module.exports = { ReportController };
