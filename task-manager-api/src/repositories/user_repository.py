from sqlalchemy import func, select

from ..models import Task, User
from .base import BaseRepository


class UserRepository(BaseRepository):
    model = User

    def list_with_task_counts(self, page):
        """`[(user, task_count)]`. Antes `len(u.tasks)` carregava a coleção
        inteira de cada usuário só para contá-la (AP-13)."""
        task_count = (
            select(func.count(Task.id))
            .where(Task.user_id == User.id)
            .correlate(User)
            .scalar_subquery()
        )
        statement, total = self._paginated(select(User).order_by(User.id), page)
        statement = statement.add_columns(task_count)
        return [tuple(row) for row in self.session.execute(statement).all()], total

    def list_all(self):
        return self.session.scalars(select(User).order_by(User.id)).all()

    def get_by_email(self, email):
        return self.session.scalars(select(User).where(User.email == email)).first()
