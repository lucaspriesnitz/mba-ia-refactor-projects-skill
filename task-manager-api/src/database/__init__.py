"""Extensões de banco e inicialização explícita.

Antes: `db` global em `database.py:3` e `db.create_all()` rodando como efeito de
importar `app.py` (`app.py:30-31`). Agora o schema é versionado por migrations
(Flask-Migrate/Alembic, pasta `migrations/`) e só é aplicado por comando
explícito (`flask --app wsgi db upgrade`) -- importar a app não toca o banco.
"""

from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import event

from ..config import PROJECT_ROOT

db = SQLAlchemy()
migrate = Migrate(directory=str(PROJECT_ROOT / "migrations"), render_as_batch=True)


def init_database(app):
    db.init_app(app)
    migrate.init_app(app, db)
    with app.app_context():
        if db.engine.dialect.name == "sqlite":
            event.listen(db.engine, "connect", _enable_sqlite_foreign_keys)


def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record):
    # SQLite ignora FKs por padrão; sem isso o `ondelete='SET NULL'` dos models
    # não teria efeito e voltaríamos a ter tasks apontando para linhas apagadas.
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()
