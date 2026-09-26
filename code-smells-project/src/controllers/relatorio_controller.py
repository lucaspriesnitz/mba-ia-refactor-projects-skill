from flask import Blueprint

from .envelope import resposta_de_sucesso
from .suporte import container

relatorio_bp = Blueprint("relatorios", __name__)


@relatorio_bp.get("/relatorios/vendas")
def relatorio_vendas():
    relatorio = container().relatorio_service.vendas()
    return resposta_de_sucesso(dados=relatorio)
