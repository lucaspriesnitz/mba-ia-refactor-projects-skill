"""`/` e `/health`, antes definidas direto em `app.py:22-28`."""

from datetime import datetime

from flask import Blueprint

API_VERSION = "1.0"

health_bp = Blueprint("health", __name__)


@health_bp.get("/health")
def health():
    return {"status": "ok", "timestamp": str(datetime.now())}


@health_bp.get("/")
def index():
    return {"message": "Task Manager API", "version": API_VERSION}
