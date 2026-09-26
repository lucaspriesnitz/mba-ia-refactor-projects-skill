'use strict';

/**
 * Entry point: lê a configuração, monta o grafo de dependências, sobe o
 * servidor e encerra com graciosidade.
 */

const { carregarConfig, ConfiguracaoInvalida } = require('./config');
const { criarLogger } = require('./config/logger');
const { criarContainer } = require('./container');
const { criarApp } = require('./app');

async function main() {
    let config;
    try {
        config = carregarConfig();
    } catch (erro) {
        if (erro instanceof ConfiguracaoInvalida) {
            // Antes de haver logger: configuração inválida derruba o boot na hora.
            console.error(`[config] ${erro.message}`);
            process.exit(1);
        }
        throw erro;
    }

    const logger = criarLogger(config);
    const container = await criarContainer(config, logger);
    const app = criarApp(container);

    const server = app.listen(config.port, config.host, () => {
        logger.info(
            { host: config.host, port: config.port, env: config.nodeEnv },
            'ecommerce-api no ar'
        );
    });

    const encerrar = (sinal) => async () => {
        logger.info({ sinal }, 'Encerrando');
        server.close(async () => {
            await container.db.close().catch(() => {});
            process.exit(0);
        });
    };

    process.on('SIGTERM', encerrar('SIGTERM'));
    process.on('SIGINT', encerrar('SIGINT'));

    // Rede de segurança: antes, um `err` ignorado dentro de callback derrubava o
    // processo em silêncio (`AppManager.js:92-93`). Agora fica registrado.
    process.on('unhandledRejection', (motivo) => {
        logger.error({ err: motivo }, 'Promise rejeitada sem tratamento');
    });
}

main().catch((erro) => {
    console.error('Falha no boot:', erro);
    process.exit(1);
});
