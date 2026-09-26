from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import joinedload

from ..models import Task
from ..models.domain import TaskStatus
from .base import BaseRepository


class TaskRepository(BaseRepository):
    model = Task

    def list_with_relations(self, page):
        """`GET /tasks`: antes 1 + 2N queries (`User.query.get` e
        `Category.query.get` por task, AP-13). Agora 1 query com JOIN."""
        statement, total = self._paginated(select(Task).order_by(Task.id), page)
        statement = statement.options(joinedload(Task.user), joinedload(Task.category))
        return self.session.scalars(statement).unique().all(), total

    def search(self, page, text=None, status=None, priority=None, user_id=None):
        statement = select(Task).order_by(Task.id)
        if text:
            pattern = f"%{text}%"
            statement = statement.where(or_(Task.title.like(pattern), Task.description.like(pattern)))
        if status:
            statement = statement.where(Task.status == status)
        if priority is not None:
            statement = statement.where(Task.priority == priority)
        if user_id is not None:
            statement = statement.where(Task.user_id == user_id)
        statement, total = self._paginated(statement, page)
        return self.session.scalars(statement).all(), total

    def list_by_user(self, user_id):
        return self.session.scalars(
            select(Task).where(Task.user_id == user_id).order_by(Task.id)
        ).all()

    def list_overdue(self, now):
        return self.session.scalars(
            select(Task).where(Task.is_overdue(now)).order_by(Task.id)
        ).all()

    def count_overdue(self, now):
        return self._count_where(Task.is_overdue(now))

    def count_by_status(self):
        rows = self.session.execute(
            select(Task.status, func.count()).group_by(Task.status)
        ).all()
        return dict(rows)

    def count_by_priority(self):
        rows = self.session.execute(
            select(Task.priority, func.count()).group_by(Task.priority)
        ).all()
        return dict(rows)

    def count_created_since(self, moment):
        return self._count_where(Task.created_at >= moment)

    def count_completed_since(self, moment):
        return self._count_where(Task.status == TaskStatus.DONE, Task.updated_at >= moment)

    def totals_by_user(self):
        """`{user_id: (total, concluídas)}` num único GROUP BY -- antes era
        uma query por usuário no laço de `report_routes.py:55-56`."""
        done = func.sum(case((Task.status == TaskStatus.DONE, 1), else_=0))
        rows = self.session.execute(
            select(Task.user_id, func.count(Task.id), done)
            .where(Task.user_id.is_not(None))
            .group_by(Task.user_id)
        ).all()
        return {user_id: (total, int(completed or 0)) for user_id, total, completed in rows}

    def _count_where(self, *conditions):
        return self.session.scalar(select(func.count()).select_from(Task).where(*conditions))
