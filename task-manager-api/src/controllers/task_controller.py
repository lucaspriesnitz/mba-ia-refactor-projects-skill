"""HTTP <-> TaskService. Rotas e formatos de resposta idênticos ao original."""

from flask import Blueprint, jsonify, request

from ..schemas import (
    load_input,
    task_detail_schema,
    task_input_schema,
    task_list_item_schema,
    task_schema,
    task_update_schema,
)
from .support import container, json_body, optional_int_arg, page_from_request, paginated_response

task_bp = Blueprint("tasks", __name__)


def _tasks():
    return container().tasks


@task_bp.get("/tasks")
def list_tasks():
    tasks, total = _tasks().list_tasks(page_from_request())
    return paginated_response(task_list_item_schema.dump(tasks, many=True), total)


@task_bp.get("/tasks/<int:task_id>")
def get_task(task_id):
    return jsonify(task_detail_schema.dump(_tasks().get_task(task_id))), 200


@task_bp.post("/tasks")
def create_task():
    data = load_input(task_input_schema, json_body())
    return jsonify(task_schema.dump(_tasks().create_task(data))), 201


@task_bp.put("/tasks/<int:task_id>")
def update_task(task_id):
    task = _tasks().get_task(task_id)
    changes = load_input(task_update_schema, json_body())
    return jsonify(task_schema.dump(_tasks().update_task(task, changes))), 200


@task_bp.delete("/tasks/<int:task_id>")
def delete_task(task_id):
    _tasks().delete_task(task_id)
    return jsonify({"message": "Task deletada com sucesso"}), 200


@task_bp.get("/tasks/search")
def search_tasks():
    tasks, total = _tasks().search_tasks(
        page_from_request(),
        text=request.args.get("q", ""),
        status=request.args.get("status", ""),
        priority=optional_int_arg("priority"),
        user_id=optional_int_arg("user_id"),
    )
    return paginated_response(task_schema.dump(tasks, many=True), total)


@task_bp.get("/tasks/stats")
def task_stats():
    return jsonify(_tasks().stats()), 200
