"""Controller de relatórios.

EXCEÇÃO CRÍTICA (AP-06): rotas de relatórios agora exigem autenticação admin.
A correção do CRITICAL prevalece sobre preservar o contrato original da rota.
"""

from flask import Blueprint

from ..middlewares.auth import requer_papel
from ..models.constants import PAPEL_ADMIN
from .envelope import resposta_de_sucesso
from .suporte import container

relatorio_bp = Blueprint("relatorios", __name__)


@relatorio_bp.get("/relatorios/vendas")
@requer_papel(PAPEL_ADMIN)
def relatorio_vendas():
    relatorio = container().relatorio_service.vendas()
    return resposta_de_sucesso(dados=relatorio)
