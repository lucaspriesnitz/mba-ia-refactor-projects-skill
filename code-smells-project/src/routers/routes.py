"""Registro de rotas.

Antes eram 16 `add_url_rule` no entry point, apontando para funções de um módulo
único (`app.py:11-30`). Agora cada recurso tem seu blueprint e o mapeamento
rota -> controller mora junto do controller; este módulo só monta.

As rotas, os métodos e os nomes dos parâmetros de caminho são exatamente os
originais.
"""

from ..controllers import BLUEPRINTS


def registrar_rotas(app):
    for blueprint in BLUEPRINTS:
        app.register_blueprint(blueprint)
