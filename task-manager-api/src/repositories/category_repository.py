from sqlalchemy import func, select

from ..models import Category, Task
from .base import BaseRepository


class CategoryRepository(BaseRepository):
    model = Category

    def list_with_task_counts(self, page):
        """`[(category, task_count)]`. Antes um `count()` por categoria (AP-13)."""
        task_count = (
            select(func.count(Task.id))
            .where(Task.category_id == Category.id)
            .correlate(Category)
            .scalar_subquery()
        )
        statement, total = self._paginated(select(Category).order_by(Category.id), page)
        statement = statement.add_columns(task_count)
        return [tuple(row) for row in self.session.execute(statement).all()], total
