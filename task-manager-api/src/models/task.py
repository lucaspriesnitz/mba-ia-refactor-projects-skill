from sqlalchemy import and_
from sqlalchemy.ext.hybrid import hybrid_method

from ..database import db
from .domain import CLOSED_STATUSES, DEFAULT_PRIORITY, TaskStatus, utc_now


class Task(db.Model):
    __tablename__ = "tasks"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(50), default=TaskStatus.PENDING.value)
    priority = db.Column(db.Integer, default=DEFAULT_PRIORITY)
    # ondelete explícito: apagar usuário/categoria desassocia a task em vez de
    # deixá-la apontando para uma linha inexistente (ou apagá-la junto).
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    category_id = db.Column(
        db.Integer, db.ForeignKey("categories.id", ondelete="SET NULL"), nullable=True
    )
    created_at = db.Column(db.DateTime, default=utc_now)
    updated_at = db.Column(db.DateTime, default=utc_now, onupdate=utc_now)
    due_date = db.Column(db.DateTime, nullable=True)
    tags = db.Column(db.String(500), nullable=True)

    user = db.relationship("User", back_populates="tasks")
    category = db.relationship("Category", back_populates="tasks")

    @hybrid_method
    def is_overdue(self, now=None):
        """Definição canônica de "atrasada" -- vale em Python e em SQL."""
        now = now or utc_now()
        return (
            self.due_date is not None
            and self.due_date < now
            and self.status not in CLOSED_STATUSES
        )

    @is_overdue.inplace.expression
    @classmethod
    def _is_overdue_expression(cls, now=None):
        now = now or utc_now()
        return and_(
            cls.due_date.is_not(None),
            cls.due_date < now,
            cls.status.not_in(CLOSED_STATUSES),
        )
