"""Entry point de desenvolvimento.

Antes: app criado no import, `SECRET_KEY` literal, `db.create_all()` no import e
`app.run(debug=True, host='0.0.0.0')`. Agora este arquivo só resolve a config e
sobe o servidor de dev; `debug` e `host` vêm do ambiente, com defaults seguros.

Em produção, use um servidor WSGI apontando para `wsgi:app`
(ex.: `waitress-serve --port=5000 wsgi:app`).
"""

from src.app_factory import create_app
from src.config import load_settings

if __name__ == "__main__":
    settings = load_settings()
    app = create_app(settings)
    app.run(host=settings.host, port=settings.port, debug=settings.debug)
