"""Alvo WSGI para servidor de produção (gunicorn/waitress).

Fecha a parte do AP-07 que dizia respeito a servir a aplicação com o servidor de
desenvolvimento do Flask.
"""

from src.app_factory import criar_app

app = criar_app()
