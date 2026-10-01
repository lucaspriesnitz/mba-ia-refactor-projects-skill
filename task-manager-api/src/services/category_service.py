"""CRUD de categorias -- antes pendurado no blueprint de relatórios
(`report_routes.py:157-223`).

EXCEÇÃO CRÍTICA (AP-06): operações de escrita (create/update/delete) exigem
autenticação admin. A correção do CRITICAL prevalece sobre preservar o contrato
original da rota.
"""

import logging

from ..errors import Forbidden, NotFound, Unauthenticated
from ..models import Category
from ..models.domain import DEFAULT_CATEGORY_COLOR

logger = logging.getLogger(__name__)


class CategoryService:
    def __init__(self, category_repository, user_repository):
        self._categories = category_repository
        self._users = user_repository

    def list_categories(self, page):
        return self._categories.list_with_task_counts(page)

    def get_category(self, category_id):
        category = self._categories.get(category_id)
        if category is None:
            raise NotFound("Categoria não encontrada")
        return category

    def _require_admin(self, actor):
        if actor is None:
            raise Unauthenticated("Autenticação necessária")
        user = self._users.get(actor.user_id)
        if user is None or not user.active:
            raise Unauthenticated("Token inválido")
        if not user.is_admin:
            raise Forbidden("Apenas administradores podem gerenciar categorias")

    def create_category(self, data, actor=None):
        self._require_admin(actor)
        category = Category(
            name=data["name"],
            description=data.get("description", ""),
            color=data.get("color", DEFAULT_CATEGORY_COLOR),
        )
        self._categories.add(category)
        self._categories.commit()
        logger.info("Categoria criada: %s", category.id)
        return category

    def update_category(self, category, changes, actor=None):
        self._require_admin(actor)
        for field, value in changes.items():
            setattr(category, field, value)
        self._categories.commit()
        return category

    def delete_category(self, category_id, actor=None):
        """Tasks da categoria ficam com `category_id = NULL` (FK `ON DELETE SET
        NULL`), em vez de apontarem para uma categoria inexistente.
        
        EXCEÇÃO CRÍTICA (AP-06): exige autenticação admin.
        """
        self._require_admin(actor)
        category = self.get_category(category_id)
        self._categories.delete(category)
        self._categories.commit()
        logger.info("Categoria deletada: %s", category_id)
