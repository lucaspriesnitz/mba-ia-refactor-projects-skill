from marshmallow import EXCLUDE, Schema, fields, validate


class CategoryInputSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    name = fields.String(
        required=True,
        validate=validate.Length(min=1, error="Nome é obrigatório"),
        error_messages={"required": "Nome é obrigatório", "null": "Nome é obrigatório", "invalid": "Nome inválido"},
    )
    description = fields.String(allow_none=True, error_messages={"invalid": "Descrição inválida"})
    color = fields.String(allow_none=True, error_messages={"invalid": "Cor inválida"})


class CategorySchema(Schema):
    id = fields.Integer()
    name = fields.String()
    description = fields.String()
    color = fields.String()
    created_at = fields.Function(lambda category: str(category.created_at))


category_input_schema = CategoryInputSchema()
category_update_schema = CategoryInputSchema(partial=True)
category_schema = CategorySchema()
