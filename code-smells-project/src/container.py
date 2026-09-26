"""Grafo de dependências da aplicação.

Ninguém instancia repository ou service no meio do código: tudo é montado aqui,
uma vez, e os controllers pegam o que precisam por `container()`. É o que
substitui o `from database import get_db` espalhado por três módulos.
"""

from .repositories import (
    HealthRepository,
    PedidoRepository,
    ProdutoRepository,
    RelatorioRepository,
    UsuarioRepository,
)
from .services import (
    AuthService,
    HealthService,
    NotificationService,
    PedidoService,
    ProdutoService,
    RelatorioService,
    UsuarioService,
)


class Container:
    def __init__(self, settings, provedor_conexao):
        self.settings = settings

        produto_repository = ProdutoRepository(provedor_conexao)
        usuario_repository = UsuarioRepository(provedor_conexao)
        pedido_repository = PedidoRepository(provedor_conexao)
        relatorio_repository = RelatorioRepository(provedor_conexao)
        health_repository = HealthRepository(provedor_conexao)

        self.auth_service = AuthService(
            settings.secret_key, settings.token_ttl_segundos
        )
        self.notification_service = NotificationService()
        self.produto_service = ProdutoService(produto_repository, provedor_conexao)
        self.usuario_service = UsuarioService(
            usuario_repository, self.auth_service, provedor_conexao
        )
        self.pedido_service = PedidoService(
            pedido_repository,
            produto_repository,
            self.notification_service,
            provedor_conexao,
        )
        self.relatorio_service = RelatorioService(relatorio_repository)
        self.health_service = HealthService(
            health_repository, provedor_conexao, settings.versao_api
        )
