"""Registro de rotas: cada recurso tem seu blueprint (junto do controller);
aqui só se monta. Caminhos, métodos e parâmetros de caminho são os originais."""

from ..controllers import BLUEPRINTS


def register_routes(app):
    for blueprint in BLUEPRINTS:
        app.register_blueprint(blueprint)
