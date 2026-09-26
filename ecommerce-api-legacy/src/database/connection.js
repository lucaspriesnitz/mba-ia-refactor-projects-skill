'use strict';

/**
 * Conexão SQLite encapsulada e promisificada.
 *
 * O driver `sqlite3` é callback-only (achado de deprecated) -- foi ele que
 * produziu o aninhamento de 6 níveis em `AppManager.js:28-78` e o N+1 de
 * `:83-106`. Este módulo é a única fronteira que ainda vê callbacks; tudo acima
 * usa `async/await`, o que elimina por construção a classe de defeito em que
 * um `err` ignorado derrubava o processo.
 */

const fs = require('node:fs');
const path = require('node:path');

class Database {
    #db;
    #fila = Promise.resolve();

    constructor(db) {
        this.#db = db;
    }

    /** Abre (e cria, se preciso) o arquivo do banco. AP-08: nada de `:memory:`. */
    static async abrir({ dbPath, verbose }, logger) {
        const sqlite3 = verbose ? require('sqlite3').verbose() : require('sqlite3');

        if (dbPath !== ':memory:') {
            fs.mkdirSync(path.dirname(path.resolve(dbPath)), { recursive: true });
        }

        const handle = await new Promise((resolve, reject) => {
            const db = new sqlite3.Database(dbPath, (err) => (err ? reject(err) : resolve(db)));
        });
        // Modo serializado: uma operação por vez nesta conexão.
        handle.serialize();

        const database = new Database(handle);
        // Sem este PRAGMA o SQLite aceita FK declarada e não a valida.
        await database.exec('PRAGMA foreign_keys = ON');
        logger.info({ dbPath }, 'Banco de dados conectado');
        return database;
    }

    run(sql, params = []) {
        return new Promise((resolve, reject) => {
            this.#db.run(sql, params, function callback(err) {
                if (err) return reject(err);
                resolve({ lastID: this.lastID, changes: this.changes });
            });
        });
    }

    get(sql, params = []) {
        return new Promise((resolve, reject) => {
            this.#db.get(sql, params, (err, row) => (err ? reject(err) : resolve(row)));
        });
    }

    all(sql, params = []) {
        return new Promise((resolve, reject) => {
            this.#db.all(sql, params, (err, rows) => (err ? reject(err) : resolve(rows || [])));
        });
    }

    exec(sql) {
        return new Promise((resolve, reject) => {
            this.#db.exec(sql, (err) => (err ? reject(err) : resolve()));
        });
    }

    /**
     * Unidade de trabalho: BEGIN/COMMIT/ROLLBACK numa única conexão.
     *
     * Fecha o achado de escrita multi-tabela sem transação (`AppManager.js:50-62`).
     * As transações são serializadas numa fila porque a conexão é compartilhada
     * entre requisições -- duas transações intercaladas na mesma conexão
     * virariam uma só.
     */
    transaction(trabalho) {
        const execucao = this.#fila.then(async () => {
            await this.exec('BEGIN IMMEDIATE');
            try {
                const resultado = await trabalho(this);
                await this.exec('COMMIT');
                return resultado;
            } catch (erro) {
                await this.exec('ROLLBACK').catch(() => {});
                throw erro;
            }
        });

        // A fila nunca deve quebrar por causa de uma transação que falhou.
        this.#fila = execucao.then(() => undefined, () => undefined);
        return execucao;
    }

    close() {
        return new Promise((resolve, reject) => {
            this.#db.close((err) => (err ? reject(err) : resolve()));
        });
    }
}

module.exports = { Database };
