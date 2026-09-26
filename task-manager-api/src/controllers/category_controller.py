"""HTTP <-> CategoryService. Antes registrado no `report_bp`; caminhos e métodos
são os mesmos."""

from flask import Blueprint, jsonify

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
def create_category():
    data = load_input(category_input_schema, json_body())
    return jsonify(category_schema.dump(_categories().create_category(data))), 201


@category_bp.put("/categories/<int:cat_id>")
def update_category(cat_id):
    category = _categories().get_category(cat_id)
    changes = load_input(category_update_schema, json_body())
    return jsonify(category_schema.dump(_categories().update_category(category, changes))), 200


@category_bp.delete("/categories/<int:cat_id>")
def delete_category(cat_id):
    _categories().delete_category(cat_id)
    return jsonify({"message": "Categoria deletada"}), 200
