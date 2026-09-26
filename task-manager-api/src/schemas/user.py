from marshmallow import EXCLUDE, Schema, fields, validate

from ..models.domain import USER_ROLES

# Antes idêntica em `user_routes.py:61,106` e `utils/helpers.py:21`.
EMAIL_PATTERN = r"^[a-zA-Z0-9+_.-]+@[a-zA-Z0-9.-]+$"

_role = fields.String(
    validate=validate.OneOf(USER_ROLES, error="Role inválido"),
    error_messages={"null": "Role inválido", "invalid": "Role inválido"},
)
_email_rule = validate.Regexp(EMAIL_PATTERN, error="Email inválido")


class UserCreateSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    name = fields.String(
        required=True,
        validate=validate.Length(min=1, error="Nome é obrigatório"),
        error_messages={"required": "Nome é obrigatório", "null": "Nome é obrigatório"},
    )
    email = fields.String(
        required=True,
        validate=[validate.Length(min=1, error="Email é obrigatório"), _email_rule],
        error_messages={"required": "Email é obrigatório", "null": "Email é obrigatório", "invalid": "Email inválido"},
    )
    password = fields.String(
        required=True,
        validate=validate.Length(min=1, error="Senha é obrigatória"),
        error_messages={"required": "Senha é obrigatória", "null": "Senha é obrigatória", "invalid": "Senha inválida"},
    )
    role = _role


class UserUpdateSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    name = fields.String(
        validate=validate.Length(min=1, error="Nome é obrigatório"),
        error_messages={"null": "Nome é obrigatório", "invalid": "Nome inválido"},
    )
    email = fields.String(
        validate=_email_rule,
        error_messages={"null": "Email inválido", "invalid": "Email inválido"},
    )
    password = fields.String(error_messages={"null": "Senha inválida", "invalid": "Senha inválida"})
    # Exigida quando o próprio usuário troca a senha (achado HIGH da auditoria).
    current_password = fields.String(error_messages={"null": "Senha atual inválida", "invalid": "Senha atual inválida"})
    role = _role
    active = fields.Boolean(error_messages={"null": "Campo active inválido", "invalid": "Campo active inválido"})


_LOGIN_REQUIRED = "Email e senha são obrigatórios"


def _login_field():
    return fields.String(
        required=True,
        validate=validate.Length(min=1, error=_LOGIN_REQUIRED),
        error_messages={"required": _LOGIN_REQUIRED, "null": _LOGIN_REQUIRED, "invalid": _LOGIN_REQUIRED},
    )


class LoginSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    email = _login_field()
    password = _login_field()


class UserSchema(Schema):
    """Allowlist de saída: o hash de senha não existe aqui (fecha AP-03)."""

    id = fields.Integer()
    name = fields.String()
    email = fields.String()
    role = fields.String()
    active = fields.Boolean()
    created_at = fields.Function(lambda user: str(user.created_at))


user_create_schema = UserCreateSchema()
user_update_schema = UserUpdateSchema()
login_schema = LoginSchema()
user_schema = UserSchema()
