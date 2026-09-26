'use strict';

/**
 * Fonte única de configuração: tudo vem do ambiente, nada fica no código.
 *
 * Fecha AP-02 (segredos hardcoded em `utils.js:2-6`). Um `.env` na raiz é lido
 * como conveniência de desenvolvimento -- variáveis já presentes no ambiente
 * têm precedência. Variáveis obrigatórias ausentes derrubam o boot (fail-fast),
 * em vez de deixar a aplicação subir com credencial vazia.
 */

const fs = require('node:fs');
const path = require('node:path');

const RAIZ_DO_PROJETO = path.resolve(__dirname, '..', '..');
const ARQUIVO_ENV = path.join(RAIZ_DO_PROJETO, '.env');

class ConfiguracaoInvalida extends Error {
    constructor(mensagem) {
        super(mensagem);
        this.name = 'ConfiguracaoInvalida';
    }
}

function carregarArquivoEnv(caminho = ARQUIVO_ENV) {
    if (!fs.existsSync(caminho)) return;

    for (const linha of fs.readFileSync(caminho, 'utf8').split(/\r?\n/)) {
        const conteudo = linha.trim();
        if (!conteudo || conteudo.startsWith('#') || !conteudo.includes('=')) continue;

        const separador = conteudo.indexOf('=');
        const chave = conteudo.slice(0, separador).trim();
        const valor = conteudo.slice(separador + 1).trim().replace(/^["']|["']$/g, '');
        if (!(chave in process.env)) process.env[chave] = valor;
    }
}

const texto = (nome, padrao) => (process.env[nome] || '').trim() || padrao;

function obrigatorio(nome, tamanhoMinimo = 1) {
    const valor = (process.env[nome] || '').trim();
    if (!valor) {
        throw new ConfiguracaoInvalida(
            `Variável de ambiente obrigatória ausente: ${nome}. ` +
            'Copie .env.example para .env e preencha os valores.'
        );
    }
    if (valor.length < tamanhoMinimo) {
        throw new ConfiguracaoInvalida(`${nome} precisa ter ao menos ${tamanhoMinimo} caracteres.`);
    }
    return valor;
}

function booleano(nome, padrao) {
    const valor = (process.env[nome] || '').trim().toLowerCase();
    if (!valor) return padrao;
    return ['1', 'true', 'yes', 'on', 'sim'].includes(valor);
}

function inteiro(nome, padrao) {
    const valor = (process.env[nome] || '').trim();
    if (!valor) return padrao;
    const numero = Number.parseInt(valor, 10);
    if (Number.isNaN(numero)) {
        throw new ConfiguracaoInvalida(`${nome} precisa ser um número inteiro, recebido: ${valor}`);
    }
    return numero;
}

function carregarConfig() {
    carregarArquivoEnv();

    const nodeEnv = texto('NODE_ENV', 'development');
    const producao = nodeEnv === 'production';

    return {
        nodeEnv,
        producao,
        host: texto('HOST', '0.0.0.0'),
        port: inteiro('PORT', 3000),
        logLevel: texto('LOG_LEVEL', producao ? 'info' : 'debug'),

        // Persistência real em arquivo (AP-08): o `:memory:` original perdia
        // todo checkout no restart.
        dbPath: texto('DB_PATH', path.join(RAIZ_DO_PROJETO, 'data', 'app.db')),
        // `.verbose()` incondicional era um achado de deprecated: agora é opt-in
        // e nunca liga em produção.
        dbVerbose: booleano('SQLITE_VERBOSE', false) && !producao,
        // Seeds são dado de desenvolvimento, não de aplicação.
        seedEnabled: booleano('SEED_ENABLED', !producao),
        seedPassword: texto('SEED_USER_PASSWORD', 'dev-seed-password'),

        // Credencial das rotas administrativas (AP-06). Sem ela o processo não sobe.
        adminApiToken: obrigatorio('ADMIN_API_TOKEN', 16),

        payment: {
            driver: texto('PAYMENT_GATEWAY_DRIVER', 'fake'),
            apiKey: obrigatorio('PAYMENT_GATEWAY_KEY'),
        },
    };
}

module.exports = { carregarConfig, ConfiguracaoInvalida, RAIZ_DO_PROJETO };
