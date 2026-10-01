"""HTTP <-> UserService / AuthService.

Rotas e formatos preservados, exceto pelo campo `password` (hash), que deixou
de sair em `GET/POST/PUT /users*` e `POST /login` -- mudança homologada (AP-03).

EXCEÇÃO CRÍTICA (AP-06): DELETE /users/<id> agora exige autenticação (admin ou
próprio usuário). GET /users, /users/<id> e /users/<id>/tasks agora exigem
autenticação. A correção do CRITICAL prevalece sobre preservar o contrato
original da rota.
"""

from flask import Blueprint, jsonify

from ..middlewares import current_actor, requer_autenticacao
from ..schemas import (
    load_input,
    login_schema,
    task_schema,
    user_create_schema,
    user_schema,
    user_task_schema,
    user_update_schema,
)
from .support import container, json_body, page_from_request, paginated_response

user_bp = Blueprint("users", __name__)


def _users():
    return container().users


@user_bp.get("/users")
@requer_autenticacao
def list_users():
    rows, total = _users().list_users(page_from_request())
    items = [{**user_schema.dump(user), "task_count": task_count} for user, task_count in rows]
    return paginated_response(items, total)


@user_bp.get("/users/<int:user_id>")
@requer_autenticacao
def get_user(user_id):
    user = _users().get_user(user_id)
    tasks = _users().get_user_tasks(user_id)
    return jsonify({**user_schema.dump(user), "tasks": task_schema.dump(tasks, many=True)}), 200


@user_bp.post("/users")
def create_user():
    data = load_input(user_create_schema, json_body())
    user = _users().create_user(data, actor=current_actor())
    return jsonify(user_schema.dump(user)), 201


@user_bp.put("/users/<int:user_id>")
@requer_autenticacao
def update_user(user_id):
    user = _users().get_user(user_id)
    changes = load_input(user_update_schema, json_body())
    user = _users().update_user(user, changes, actor=current_actor())
    return jsonify(user_schema.dump(user)), 200


@user_bp.delete("/users/<int:user_id>")
@requer_autenticacao
def delete_user(user_id):
    _users().delete_user(user_id, actor=current_actor())
    return jsonify({"message": "Usuário deletado com sucesso"}), 200


@user_bp.get("/users/<int:user_id>/tasks")
@requer_autenticacao
def get_user_tasks(user_id):
    tasks = _users().get_user_tasks(user_id)
    return jsonify(user_task_schema.dump(tasks, many=True)), 200


@user_bp.post("/login")
def login():
    credentials = load_input(login_schema, json_body())
    user, token = container().auth.login(credentials["email"], credentials["password"])
    return jsonify({
        "message": "Login realizado com sucesso",
        "user": user_schema.dump(user),
        "token": token,
    }), 200
