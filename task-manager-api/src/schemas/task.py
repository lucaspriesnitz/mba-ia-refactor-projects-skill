from datetime import datetime

from marshmallow import EXCLUDE, Schema, ValidationError, fields, validate

from ..models.domain import (
    DUE_DATE_FORMAT,
    PRIORITY_MAX,
    PRIORITY_MIN,
    TASK_STATUSES,
    TITLE_MAX_LENGTH,
    TITLE_MIN_LENGTH,
)

PRIORITY_MESSAGE = f"Prioridade deve ser entre {PRIORITY_MIN} e {PRIORITY_MAX}"
DUE_DATE_MESSAGE = "Formato de data inválido. Use YYYY-MM-DD"


def _validate_title(title):
    if not title:
        raise ValidationError("Título é obrigatório")
    if len(title) < TITLE_MIN_LENGTH:
        raise ValidationError("Título muito curto")
    if len(title) > TITLE_MAX_LENGTH:
        raise ValidationError("Título muito longo")


class DueDate(fields.Field):
    """`"YYYY-MM-DD"` -> datetime; vazio/nulo -> None (limpa o prazo)."""

    def _deserialize(self, value, attr, data, **kwargs):
        if value in (None, ""):
            return None
        if not isinstance(value, str):
            raise ValidationError(DUE_DATE_MESSAGE)
        try:
            return datetime.strptime(value, DUE_DATE_FORMAT)
        except ValueError:
            raise ValidationError(DUE_DATE_MESSAGE)


class Tags(fields.Field):
    """Lista de strings -> `"a,b"`; string passa como está (formato de armazenamento)."""

    def _deserialize(self, value, attr, data, **kwargs):
        if isinstance(value, list) and all(isinstance(tag, str) for tag in value):
            return ",".join(value)
        if isinstance(value, str):
            return value
        raise ValidationError("Tags inválidas")


class TaskInputSchema(Schema):
    """Criação e atualização (`partial=True`). Defaults são aplicados no service."""

    class Meta:
        unknown = EXCLUDE

    title = fields.String(
        required=True,
        validate=_validate_title,
        error_messages={
            "required": "Título é obrigatório",
            "null": "Título é obrigatório",
            "invalid": "Título inválido",
        },
    )
    description = fields.String(allow_none=True, error_messages={"invalid": "Descrição inválida"})
    status = fields.String(
        validate=validate.OneOf(TASK_STATUSES, error="Status inválido"),
        error_messages={"null": "Status inválido", "invalid": "Status inválido"},
    )
    priority = fields.Integer(
        strict=True,
        validate=validate.Range(min=PRIORITY_MIN, max=PRIORITY_MAX, error=PRIORITY_MESSAGE),
        error_messages={"null": PRIORITY_MESSAGE, "invalid": PRIORITY_MESSAGE},
    )
    user_id = fields.Integer(allow_none=True, error_messages={"invalid": "user_id inválido"})
    category_id = fields.Integer(allow_none=True, error_messages={"invalid": "category_id inválido"})
    due_date = DueDate(allow_none=True)
    tags = Tags(allow_none=True)


class TaskSchema(Schema):
    """Serialização canônica de task (antes remontada à mão em 3 lugares)."""

    id = fields.Integer()
    title = fields.String()
    description = fields.String()
    status = fields.String()
    priority = fields.Integer()
    user_id = fields.Integer()
    category_id = fields.Integer()
    created_at = fields.Function(lambda task: str(task.created_at))
    updated_at = fields.Function(lambda task: str(task.updated_at))
    due_date = fields.Function(lambda task: str(task.due_date) if task.due_date else None)
    tags = fields.Function(lambda task: task.tags.split(",") if task.tags else [])


class TaskDetailSchema(TaskSchema):
    overdue = fields.Function(lambda task: task.is_overdue())


class TaskListItemSchema(TaskDetailSchema):
    user_name = fields.Function(lambda task: task.user.name if task.user else None)
    category_name = fields.Function(lambda task: task.category.name if task.category else None)


# Formato resumido de `GET /users/<id>/tasks`.
USER_TASK_FIELDS = ("id", "title", "description", "status", "priority", "created_at", "due_date", "overdue")

task_input_schema = TaskInputSchema()
task_update_schema = TaskInputSchema(partial=True)
task_schema = TaskSchema()
task_detail_schema = TaskDetailSchema()
task_list_item_schema = TaskListItemSchema()
user_task_schema = TaskDetailSchema(only=USER_TASK_FIELDS)
