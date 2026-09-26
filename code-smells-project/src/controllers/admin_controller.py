"""Rotas administrativas.

Eram os dois piores buracos da aplicação e receberam tratamentos diferentes,
conforme a decisão homologada no fim da Fase 2.
"""

from flask import Blueprint

from ..middlewares.auth import requer_papel
from ..models.constants import PAPEL_ADMIN
from ..models.errors import NaoAutorizado
from .envelope import resposta_de_sucesso
from .suporte import container

admin_bp = Blueprint("admin", __name__)


@admin_bp.post("/admin/reset-db")
@requer_papel(PAPEL_ADMIN)
def reset_database():
    """Antes (`app.py:47-57`): apagava as 4 tabelas para qualquer `curl` anônimo.

    Agora exige credencial com papel `admin` (AP-06 / T-05) e, além disso, só
    roda se `ADMIN_RESET_HABILITADO` estiver ligado no ambiente -- desligado por
    padrão, como recomendado na auditoria, para não existir em produção.
    """
    if not container().settings.admin_reset_habilitado:
        raise NaoAutorizado(
            "Operação desabilitada neste ambiente (ADMIN_RESET_HABILITADO)"
        )
    container().health_service.resetar_dados()
    return resposta_de_sucesso(mensagem="Banco de dados resetado")


@admin_bp.post("/admin/query")
def executar_query():
    """Rota desativada: responde 403 e não executa nada.

    Fecha o CRITICAL AP-05 -- antes (`app.py:59-78`) esta rota lia
    `dados["sql"]` e executava a string vinda do cliente, com `commit` para
    não-SELECT: controle total do banco (DROP TABLE, dump de credenciais,
    `ATTACH DATABASE`) por qualquer pessoa na rede, sem autenticação.

    Por que a rota NÃO foi deletada: por decisão explícita do dono do projeto no
    fim da Fase 2, todos os endpoints originais precisam continuar respondendo.
    Então o caminho permanece registrado e devolve 403 de forma incondicional --
    nenhuma string SQL do cliente é lida, interpretada ou executada. Não existe
    variável de ambiente que reabilite isso: operação administrativa deve ser
    código versionado atrás de autenticação, nunca SQL vindo de fora.
    """
    raise NaoAutorizado(
        "Execução de SQL arbitrário está desabilitada permanentemente"
    )
