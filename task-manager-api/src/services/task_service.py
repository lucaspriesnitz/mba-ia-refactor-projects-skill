"""Regra de negócio de tasks -- antes dentro dos handlers de `routes/task_routes.py`
(`create_task` tinha 70 linhas de validação, FK, parsing e commit; AP-10)."""

import logging

from ..errors import NotFound
from ..models import Task
from ..models.domain import DEFAULT_PRIORITY, TASK_STATUSES, TaskStatus, completion_rate, utc_now

logger = logging.getLogger(__name__)

TASK_DEFAULTS = {"description": "", "status": TaskStatus.PENDING.value, "priority": DEFAULT_PRIORITY}


class TaskService:
    def __init__(self, task_repository, user_repository, category_repository):
        self._tasks = task_repository
        self._users = user_repository
        self._categories = category_repository

    def list_tasks(self, page):
        return self._tasks.list_with_relations(page)

    def search_tasks(self, page, text=None, status=None, priority=None, user_id=None):
        return self._tasks.search(page, text=text, status=status, priority=priority, user_id=user_id)

    def get_task(self, task_id):
        task = self._tasks.get(task_id)
        if task is None:
            raise NotFound("Task não encontrada")
        return task

    def create_task(self, data, actor=None):
        """EXCEÇÃO CRÍTICA (AP-06): exige autenticação. A task é criada com o
        user_id do ator, não do input. A correção do CRITICAL prevalece sobre
        preservar o contrato original da rota.
        """
        if actor is None:
            from ..errors import Unauthenticated
            raise Unauthenticated("Autenticação necessária")
        user = self._users.get(actor.user_id)
        if user is None or not user.active:
            from ..errors import Unauthenticated
            raise Unauthenticated("Token inválido")
        values = {**TASK_DEFAULTS, **data}
        values["user_id"] = user.id  # força o user_id do ator
        self._ensure_references_exist(values)
        task = Task(**values)
        self._tasks.add(task)
        self._tasks.commit()
        logger.info("Task criada: %s", task.id)
        return task

    def update_task(self, task, changes, actor=None):
        """EXCEÇÃO CRÍTICA (AP-06): exige autenticação. Apenas admin ou o dono
        da task pode atualizá-la. A correção do CRITICAL prevalece sobre preservar
        o contrato original da rota.
        """
        if actor is None:
            from ..errors import Unauthenticated
            raise Unauthenticated("Autenticação necessária")
        user = self._users.get(actor.user_id)
        if user is None or not user.active:
            from ..errors import Unauthenticated
            raise Unauthenticated("Token inválido")
        if not user.is_admin and task.user_id != user.id:
            from ..errors import Forbidden
            raise Forbidden("Sem permissão para alterar esta task")
        self._ensure_references_exist(changes)
        for field, value in changes.items():
            setattr(task, field, value)
        task.updated_at = utc_now()
        self._tasks.commit()
        logger.info("Task atualizada: %s", task.id)
        return task

    def delete_task(self, task_id, actor=None):
        """EXCEÇÃO CRÍTICA (AP-06): exige autenticação. Apenas admin ou o dono
        da task pode deletá-la. A correção do CRITICAL prevalece sobre preservar
        o contrato original da rota.
        """
        task = self.get_task(task_id)
        if actor is None:
            from ..errors import Unauthenticated
            raise Unauthenticated("Autenticação necessária")
        user = self._users.get(actor.user_id)
        if user is None or not user.active:
            from ..errors import Unauthenticated
            raise Unauthenticated("Token inválido")
        if not user.is_admin and task.user_id != user.id:
            from ..errors import Forbidden
            raise Forbidden("Sem permissão para deletar esta task")
        self._tasks.delete(task)
        self._tasks.commit()
        logger.info("Task deletada: %s", task_id)

    def stats(self):
        by_status = self._tasks.count_by_status()
        total = self._tasks.count()
        done = by_status.get(TaskStatus.DONE, 0)
        return {
            "total": total,
            **{status: by_status.get(status, 0) for status in TASK_STATUSES},
            "overdue": self._tasks.count_overdue(utc_now()),
            "completion_rate": completion_rate(done, total),
        }

    def _ensure_references_exist(self, values):
        if values.get("user_id") is not None and self._users.get(values["user_id"]) is None:
            raise NotFound("Usuário não encontrado")
        if values.get("category_id") is not None and self._categories.get(values["category_id"]) is None:
            raise NotFound("Categoria não encontrada")
