'use strict';

/**
 * Hash de senha com `crypto.scrypt` (AP-03 / AP-04).
 *
 * Substitui `badCrypto` (`utils.js:17-23`), que derivava 10 caracteres do
 * primeiro byte e meio da senha, sem salt e de forma determinística -- qualquer
 * senha era recuperável por tabela pré-computada.
 *
 * `scrypt` é KDF nativa do Node (sem dependência nativa para compilar, ao
 * contrário de bcrypt/argon2): salt aleatório por registro, custo calibrável e
 * comparação em tempo constante. O formato armazenado carrega os parâmetros,
 * então dá para aumentar o custo sem invalidar os hashes antigos.
 */

const { randomBytes, scrypt, timingSafeEqual } = require('node:crypto');
const { promisify } = require('node:util');

const scryptAsync = promisify(scrypt);

const CUSTO_N = 16384;
const BLOCO_R = 8;
const PARALELISMO_P = 1;
const TAMANHO_CHAVE = 64;
const ALGORITMO = 'scrypt';

async function derivar(senha, salt, { N, r, p }) {
    return scryptAsync(senha.normalize('NFKC'), salt, TAMANHO_CHAVE, {
        N,
        r,
        p,
        maxmem: 256 * N * r,
    });
}

async function hash(senha) {
    const salt = randomBytes(16);
    const chave = await derivar(senha, salt, { N: CUSTO_N, r: BLOCO_R, p: PARALELISMO_P });
    return [
        ALGORITMO,
        CUSTO_N,
        BLOCO_R,
        PARALELISMO_P,
        salt.toString('base64'),
        chave.toString('base64'),
    ].join('$');
}

async function verify(senha, armazenado) {
    if (!armazenado) return false;

    const [algoritmo, n, r, p, salt, chave] = String(armazenado).split('$');
    if (algoritmo !== ALGORITMO || !salt || !chave) return false;

    const esperado = Buffer.from(chave, 'base64');
    const obtido = await derivar(senha, Buffer.from(salt, 'base64'), {
        N: Number(n),
        r: Number(r),
        p: Number(p),
    });

    return esperado.length === obtido.length && timingSafeEqual(esperado, obtido);
}

module.exports = { hash, verify };
