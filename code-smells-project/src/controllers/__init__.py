from .admin_controller import admin_bp
from .health_controller import health_bp
from .index_controller import index_bp
from .pedido_controller import pedido_bp
from .produto_controller import produto_bp
from .relatorio_controller import relatorio_bp
from .usuario_controller import usuario_bp

BLUEPRINTS = (
    index_bp,
    produto_bp,
    usuario_bp,
    pedido_bp,
    relatorio_bp,
    health_bp,
    admin_bp,
)

__all__ = ["BLUEPRINTS"]
