"""Health check e a operação administrativa de reset.

O payload do health deixa de expor configuração interna: `secret_key`, `db_path`
e `debug` saíram (AP-02 -- decisão homologada na Fase 2). Sobra status,
conectividade, contagens e versão.
"""

import logging

from ..database.unit_of_work import transacao

logger = logging.getLogger(__name__)


class HealthService:
    def __init__(self, health_repository, provedor_conexao, versao_api):
        self._health = health_repository
        self._provedor_conexao = provedor_conexao
        self._versao_api = versao_api

    def status(self):
        contagens = self._health.contagens()
        return {
            "status": "ok",
            "database": "connected",
            "counts": contagens,
            "versao": self._versao_api,
        }

    def resetar_dados(self):
        with transacao(self._provedor_conexao):
            self._health.apagar_todos_os_dados()
        logger.warning("Banco de dados resetado por requisição administrativa")
        return True
