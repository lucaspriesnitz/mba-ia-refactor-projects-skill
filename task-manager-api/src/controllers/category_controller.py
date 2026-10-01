"""HTTP <-> CategoryService. Antes registrado no `report_bp`; caminhos e métodos
são os mesmos.

EXCEÇÃO CRÍTICA (AP-06): POST/PUT/DELETE /categories agora exigem autenticação
admin. A correção do CRITICAL prevalece sobre preservar o contrato original da rota.
"""

from flask import Blueprint, jsonify

from ..middlewares import current_actor, requer_admin
from ..schemas import category_input_schema, category_schema, category_update_schema, load_input
from .support import container, json_body, page_from_request, paginated_response

category_bp = Blueprint("categories", __name__)


def _categories():
    return container().categories


@category_bp.get("/categories")
def list_categories():
    rows, total = _categories().list_categories(page_from_request())
    items = [{**category_schema.dump(category), "task_count": count} for category, count in rows]
    return paginated_response(items, total)


@category_bp.post("/categories")
@requer_admin
def create_category():
    data = load_input(category_input_schema, json_body())
    return jsonify(category_schema.dump(_categories().create_category(data, actor=current_actor()))), 201


@category_bp.put("/categories/<int:cat_id>")
@requer_admin
def update_category(cat_id):
    category = _categories().get_category(cat_id)
    changes = load_input(category_update_schema, json_body())
    return jsonify(category_schema.dump(_categories().update_category(category, changes, actor=current_actor()))), 200


@category_bp.delete("/categories/<int:cat_id>")
@requer_admin
def delete_category(cat_id):
    _categories().delete_category(cat_id, actor=current_actor())
    return jsonify({"message": "Categoria deletada"}), 200
