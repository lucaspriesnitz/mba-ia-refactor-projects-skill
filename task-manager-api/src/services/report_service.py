"""Relatórios. Antes `summary_report` era um handler de 90 linhas com ~15
`count()` separados e uma query por usuário (`report_routes.py:12-101`); agora
são agregações com GROUP BY nas repositories e a montagem do formato aqui."""

from datetime import timedelta

from ..models.domain import (
    HIGH_PRIORITY_THRESHOLD,
    PRIORITY_LABELS,
    TASK_STATUSES,
    TaskStatus,
    completion_rate,
    utc_now,
)

RECENT_WINDOW = timedelta(days=7)


class ReportService:
    def __init__(self, task_repository, user_repository, category_repository, user_service):
        self._tasks = task_repository
        self._users = user_repository
        self._categories = category_repository
        self._user_service = user_service

    def summary(self):
        now = utc_now()
        since = now - RECENT_WINDOW
        by_status = self._tasks.count_by_status()
        by_priority = self._tasks.count_by_priority()
        overdue = self._tasks.list_overdue(now)
        totals_by_user = self._tasks.totals_by_user()

        return {
            "generated_at": str(now),
            "overview": {
                "total_tasks": self._tasks.count(),
                "total_users": self._users.count(),
                "total_categories": self._categories.count(),
            },
            "tasks_by_status": {status: by_status.get(status, 0) for status in TASK_STATUSES},
            "tasks_by_priority": {
                label: by_priority.get(priority, 0) for priority, label in PRIORITY_LABELS.items()
            },
            "overdue": {
                "count": len(overdue),
                "tasks": [
                    {
                        "id": task.id,
                        "title": task.title,
                        "due_date": str(task.due_date),
                        "days_overdue": (now - task.due_date).days,
                    }
                    for task in overdue
                ],
            },
            "recent_activity": {
                "tasks_created_last_7_days": self._tasks.count_created_since(since),
                "tasks_completed_last_7_days": self._tasks.count_completed_since(since),
            },
            "user_productivity": [
                self._productivity(user, *totals_by_user.get(user.id, (0, 0)))
                for user in self._users.list_all()
            ],
        }

    def user_report(self, user_id):
        user = self._user_service.get_user(user_id)
        tasks = self._tasks.list_by_user(user_id)
        now = utc_now()
        counts = {status: 0 for status in TASK_STATUSES}
        for task in tasks:
            if task.status in counts:
                counts[task.status] += 1

        return {
            "user": {"id": user.id, "name": user.name, "email": user.email},
            "statistics": {
                "total_tasks": len(tasks),
                **counts,
                "overdue": sum(1 for task in tasks if task.is_overdue(now)),
                "high_priority": sum(1 for task in tasks if task.priority <= HIGH_PRIORITY_THRESHOLD),
                "completion_rate": completion_rate(counts[TaskStatus.DONE], len(tasks)),
            },
        }

    @staticmethod
    def _productivity(user, total, completed):
        return {
            "user_id": user.id,
            "user_name": user.name,
            "total_tasks": total,
            "completed_tasks": completed,
            "completion_rate": completion_rate(completed, total),
        }
