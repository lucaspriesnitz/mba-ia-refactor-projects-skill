"""CRUD de categorias -- antes pendurado no blueprint de relatórios
(`report_routes.py:157-223`)."""

import logging

from ..errors import NotFound
from ..models import Category
from ..models.domain import DEFAULT_CATEGORY_COLOR

logger = logging.getLogger(__name__)


class CategoryService:
    def __init__(self, category_repository):
        self._categories = category_repository

    def list_categories(self, page):
        return self._categories.list_with_task_counts(page)

    def get_category(self, category_id):
        category = self._categories.get(category_id)
        if category is None:
            raise NotFound("Categoria não encontrada")
        return category

    def create_category(self, data):
        category = Category(
            name=data["name"],
            description=data.get("description", ""),
            color=data.get("color", DEFAULT_CATEGORY_COLOR),
        )
        self._categories.add(category)
        self._categories.commit()
        logger.info("Categoria criada: %s", category.id)
        return category

    def update_category(self, category, changes):
        for field, value in changes.items():
            setattr(category, field, value)
        self._categories.commit()
        return category

    def delete_category(self, category_id):
        """Tasks da categoria ficam com `category_id = NULL` (FK `ON DELETE SET
        NULL`), em vez de apontarem para uma categoria inexistente."""
        category = self.get_category(category_id)
        self._categories.delete(category)
        self._categories.commit()
        logger.info("Categoria deletada: %s", category_id)
