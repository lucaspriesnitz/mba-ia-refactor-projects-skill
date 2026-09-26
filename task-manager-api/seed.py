"""Popula o banco com dados de demonstração.

Aplica as migrations pendentes antes (o schema não é mais criado no import da
app) e apaga os dados existentes. Não use contra um banco com dados reais.
"""

import logging
from datetime import timedelta

from flask_migrate import upgrade
from sqlalchemy import delete

from src.app_factory import create_app
from src.database import db
from src.middlewares import configure_logging
from src.models import Category, Task, User
from src.models.domain import UserRole, utc_now
from src.security import hash_password

logger = logging.getLogger("seed")

# Credenciais de DEMONSTRAÇÃO, documentadas no README. Atendem à política de
# senha (PASSWORD_MIN_LENGTH, default 12) e são gravadas com hash scrypt.
USERS = [
    ("João Silva", "joao@email.com", "joao-demo-2026", UserRole.ADMIN),
    ("Maria Santos", "maria@email.com", "maria-demo-2026", UserRole.USER),
    ("Pedro Oliveira", "pedro@email.com", "pedro-demo-2026", UserRole.MANAGER),
]

CATEGORIES = [
    ("Backend", "Tarefas de backend", "#3498db"),
    ("Frontend", "Tarefas de frontend", "#2ecc71"),
    ("DevOps", "Tarefas de infraestrutura", "#e74c3c"),
    ("Bug", "Correção de bugs", "#e67e22"),
]


def _tasks(users, categories, now):
    u1, u2, u3 = users
    backend, frontend, devops, bug = categories
    return [
        dict(title="Implementar autenticação JWT", description="Adicionar autenticação real com JWT", status="pending", priority=1, user_id=u1.id, category_id=backend.id, due_date=now - timedelta(days=3)),
        dict(title="Criar tela de login", description="Tela de login responsiva", status="in_progress", priority=2, user_id=u2.id, category_id=frontend.id, due_date=now + timedelta(days=5)),
        dict(title="Configurar CI/CD", description="Pipeline com GitHub Actions", status="done", priority=2, user_id=u3.id, category_id=devops.id, tags="devops,ci,github"),
        dict(title="Corrigir bug no filtro de busca", description="Filtro não funciona com caracteres especiais", status="pending", priority=1, user_id=u1.id, category_id=bug.id, due_date=now - timedelta(days=1)),
        dict(title="Adicionar paginação na API", description="Endpoints retornam todos os registros", status="pending", priority=3, user_id=u1.id, category_id=backend.id, due_date=now + timedelta(days=10)),
        dict(title="Escrever testes unitários", description="Cobertura mínima de 80%", status="pending", priority=2, user_id=u2.id, category_id=backend.id),
        dict(title="Documentar API com Swagger", description="Gerar documentação automática", status="cancelled", priority=4, user_id=u3.id, category_id=backend.id),
        dict(title="Refatorar models", description="Melhorar organização dos models", status="in_progress", priority=3, user_id=u2.id, category_id=backend.id, tags="refactor,tech-debt"),
        dict(title="Configurar monitoramento", description="Prometheus + Grafana", status="pending", priority=4, user_id=u3.id, category_id=devops.id, due_date=now + timedelta(days=20)),
        dict(title="Melhorar validações de input", description="Usar marshmallow ou pydantic", status="pending", priority=3, user_id=u1.id, category_id=backend.id, tags="improvement,validation"),
    ]


def seed_data(app):
    with app.app_context():
        upgrade()
        # O fileConfig do alembic.ini rebaixa o root logger para WARN.
        configure_logging(app.extensions["container"].settings.log_level)

        for model in (Task, User, Category):
            db.session.execute(delete(model))

        users = [
            User(name=name, email=email, password_hash=hash_password(password), role=role.value)
            for name, email, password, role in USERS
        ]
        categories = [Category(name=n, description=d, color=c) for n, d, c in CATEGORIES]
        db.session.add_all(users + categories)
        db.session.flush()  # gera os ids referenciados pelas tasks

        tasks = [Task(**values) for values in _tasks(users, categories, utc_now())]
        db.session.add_all(tasks)
        db.session.commit()

        logger.info(
            "Seed concluído: %s usuários, %s categorias, %s tasks",
            len(users), len(categories), len(tasks),
        )


if __name__ == "__main__":
    seed_data(create_app())
