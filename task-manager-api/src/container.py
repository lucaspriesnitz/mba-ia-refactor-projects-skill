"""Grafo de dependências: repositories e services são montados aqui, uma vez.

Os controllers pegam o que precisam por `container()`; ninguém instancia
service no meio do código.
"""

from .repositories import CategoryRepository, TaskRepository, UserRepository
from .security import TokenService
from .services import AuthService, CategoryService, ReportService, TaskService, UserService


class Container:
    def __init__(self, settings):
        self.settings = settings

        task_repository = TaskRepository()
        user_repository = UserRepository()
        category_repository = CategoryRepository()

        self.tokens = TokenService(settings.secret_key, settings.token_ttl_seconds)
        self.tasks = TaskService(task_repository, user_repository, category_repository)
        self.users = UserService(user_repository, task_repository, settings.password_min_length)
        self.categories = CategoryService(category_repository, user_repository)
        self.auth = AuthService(user_repository, self.tokens)
        self.reports = ReportService(task_repository, user_repository, category_repository, self.users)
