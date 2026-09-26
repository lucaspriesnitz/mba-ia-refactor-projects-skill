"""Entry point.

Tudo que existia aqui antes -- segredo hardcoded, DEBUG fixo, CORS aberto, 16
`add_url_rule` e duas rotas administrativas com SQL inline -- foi para as camadas
em `src/`. Este arquivo só resolve a configuração, monta o app e sobe o servidor.

Em produção, use um servidor WSGI apontando para `wsgi:app` (ex.:
`waitress-serve --port=5000 wsgi:app`), não este `app.run`.
"""

import logging

from src.app_factory import criar_app
from src.config import carregar_settings

logger = logging.getLogger(__name__)

settings = carregar_settings()
app = criar_app(settings)


if __name__ == "__main__":
    logger.info("Servidor iniciado em http://%s:%s", settings.host, settings.port)
    app.run(host=settings.host, port=settings.port, debug=settings.debug)
