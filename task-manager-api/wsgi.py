"""Alvo WSGI de produção (`waitress-serve wsgi:app`) e da CLI (`flask --app wsgi db upgrade`)."""

from src.app_factory import create_app

app = create_app()
