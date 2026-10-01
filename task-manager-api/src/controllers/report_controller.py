"""Relatórios administrativos.

EXCEÇÃO CRÍTICA (AP-06): rotas de relatórios agora exigem autenticação admin.
A correção do CRITICAL prevalece sobre preservar o contrato original da rota.
"""

from flask import Blueprint, jsonify

from ..middlewares import requer_admin
from .support import container

report_bp = Blueprint("reports", __name__)


@report_bp.get("/reports/summary")
@requer_admin
def summary_report():
    return jsonify(container().reports.summary()), 200


@report_bp.get("/reports/user/<int:user_id>")
@requer_admin
def user_report(user_id):
    return jsonify(container().reports.user_report(user_id)), 200
