"""Health check.

O payload perdeu `secret_key`, `db_path` e `ambiente`/`debug` -- vazamento de
configuração por rota pública (AP-02), removido com aval do dono na Fase 2.
O SQL que rodava aqui dentro (`controllers.py:266-274`) foi para a repository.
"""

from flask import Blueprint, jsonify

from .suporte import container

health_bp = Blueprint("health", __name__)


@health_bp.get("/health")
def health_check():
    # O health não usa o envelope: seu corpo é o próprio relatório de status,
    # como no contrato original (`status`/`database`/`counts`/`versao`).
    return jsonify(container().health_service.status()), 200
