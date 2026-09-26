from flask import Blueprint, jsonify

from .support import container

report_bp = Blueprint("reports", __name__)


@report_bp.get("/reports/summary")
def summary_report():
    return jsonify(container().reports.summary()), 200


@report_bp.get("/reports/user/<int:user_id>")
def user_report(user_id):
    return jsonify(container().reports.user_report(user_id)), 200
