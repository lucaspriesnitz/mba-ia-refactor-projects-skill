"""Base das repositories: única camada que conhece a sessão do ORM.

Usa o estilo 2.0 (`db.select`, `db.session.get`) no lugar de `Model.query` e
`Query.get()`, ambos legados no SQLAlchemy 2.x.
"""

from dataclasses import dataclass

from sqlalchemy import func, select

from ..database import db


@dataclass(frozen=True)
class Page:
    """Janela de uma listagem. `limit=None` = sem limite (contrato original)."""

    limit: int | None = None
    offset: int = 0


class BaseRepository:
    model = None

    @property
    def session(self):
        return db.session

    def get(self, entity_id):
        return self.session.get(self.model, entity_id)

    def count(self):
        return self.session.scalar(select(func.count()).select_from(self.model))

    def add(self, entity):
        self.session.add(entity)

    def delete(self, entity):
        self.session.delete(entity)

    def commit(self):
        try:
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise

    def _paginated(self, statement, page):
        count_statement = select(func.count()).select_from(
            statement.order_by(None).subquery()
        )
        total = self.session.scalar(count_statement)
        if page.offset:
            statement = statement.offset(page.offset)
        if page.limit is not None:
            statement = statement.limit(page.limit)
        return statement, total
