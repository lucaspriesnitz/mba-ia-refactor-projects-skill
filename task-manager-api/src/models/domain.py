"""Constantes e regras de domínio -- um único ponto de verdade por regra (AP-12).

Antes a whitelist de status aparecia literal em 5 lugares, a de roles em 3 e o
cálculo de "atrasada" em 6. Todas as camadas importam daqui.
"""

from datetime import UTC, datetime
from enum import StrEnum


class TaskStatus(StrEnum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    CANCELLED = "cancelled"


class UserRole(StrEnum):
    USER = "user"
    ADMIN = "admin"
    MANAGER = "manager"


TASK_STATUSES = tuple(status.value for status in TaskStatus)
CLOSED_STATUSES = (TaskStatus.DONE.value, TaskStatus.CANCELLED.value)
USER_ROLES = tuple(role.value for role in UserRole)

TITLE_MIN_LENGTH = 3
TITLE_MAX_LENGTH = 200
PRIORITY_MIN = 1
PRIORITY_MAX = 5
DEFAULT_PRIORITY = 3
HIGH_PRIORITY_THRESHOLD = 2
DEFAULT_CATEGORY_COLOR = "#000000"
DUE_DATE_FORMAT = "%Y-%m-%d"

# Rótulos de `GET /reports/summary` -> tasks_by_priority, na ordem 1..5.
PRIORITY_LABELS = {1: "critical", 2: "high", 3: "medium", 4: "low", 5: "minimal"}


def utc_now():
    """UTC sem tzinfo, que é como as colunas `DateTime` armazenam.

    Substitui o `datetime.utcnow()` (deprecated no Python 3.12) usado em 20
    pontos. O formato serializado (`str(dt)`) permanece o mesmo.
    """
    return datetime.now(UTC).replace(tzinfo=None)


def completion_rate(completed, total):
    """Percentual com 2 casas; 0 quando não há tasks. Antes copiado em 3 lugares."""
    return round((completed / total) * 100, 2) if total > 0 else 0
