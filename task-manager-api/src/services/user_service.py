"""Regra de negócio de usuários, incluindo a autorização dos campos sensíveis.

Fecha a parte CRITICAL do AP-06: antes `PUT /users/<id>` aceitava `{"role":
"admin"}` e trocava a senha de qualquer usuário para qualquer chamador anônimo
(`user_routes.py:114-122`), e `POST /users` criava admins livremente. Agora:

- definir/alterar `role` ou `active` exige token de admin;
- trocar senha exige token do próprio usuário **com a senha atual**, ou de admin;
- os demais campos e rotas mantêm o contrato original (sem token).

O papel efetivo do chamador é relido do banco, não confiado ao token: um admin
rebaixado ou desativado perde o poder na hora, sem esperar o token expirar.
"""

import logging

from ..errors import Conflict, Forbidden, InvalidInput, NotFound, Unauthenticated
from ..models import User
from ..models.domain import UserRole
from ..security import hash_password, verify_password

logger = logging.getLogger(__name__)

ADMIN_ONLY_FIELDS = ("role", "active")


class UserService:
    def __init__(self, user_repository, task_repository, password_min_length):
        self._users = user_repository
        self._tasks = task_repository
        self._password_min_length = password_min_length

    def list_users(self, page):
        return self._users.list_with_task_counts(page)

    def get_user(self, user_id):
        user = self._users.get(user_id)
        if user is None:
            raise NotFound("Usuário não encontrado")
        return user

    def get_user_tasks(self, user_id):
        self.get_user(user_id)
        return self._tasks.list_by_user(user_id)

    def create_user(self, data, actor=None):
        role = data.get("role", UserRole.USER.value)
        if role != UserRole.USER:
            self._require_admin(actor, "definir role")
        self._check_password_policy(data["password"])
        if self._users.get_by_email(data["email"]):
            raise Conflict("Email já cadastrado")

        user = User(
            name=data["name"],
            email=data["email"],
            password_hash=hash_password(data["password"]),
            role=role,
        )
        self._users.add(user)
        self._users.commit()
        logger.info("Usuário criado: %s", user.id)
        return user

    def update_user(self, user, changes, actor=None):
        """EXCEÇÃO CRÍTICA (AP-06): exige autenticação. Apenas o próprio usuário
        ou admin pode atualizar dados. A correção do CRITICAL prevalece sobre
        preservar o contrato original da rota.
        """
        caller = self.resolve_actor(actor)
        if not caller.is_admin and caller.id != user.id:
            raise Forbidden("Sem permissão para alterar este usuário")
        if any(field in changes for field in ADMIN_ONLY_FIELDS):
            self._require_admin(actor, "alterar role/active")
        if "password" in changes:
            self._authorize_password_change(user, changes.get("current_password"), actor)
            self._check_password_policy(changes["password"])

        if "email" in changes:
            existing = self._users.get_by_email(changes["email"])
            if existing and existing.id != user.id:
                raise Conflict("Email já cadastrado")
            user.email = changes["email"]
        if "name" in changes:
            user.name = changes["name"]
        if "password" in changes:
            user.password_hash = hash_password(changes["password"])
        if "role" in changes:
            user.role = changes["role"]
        if "active" in changes:
            user.active = changes["active"]

        self._users.commit()
        logger.info("Usuário atualizado: %s", user.id)
        return user

    def delete_user(self, user_id, actor=None):
        """As tasks do usuário são desassociadas (FK `ON DELETE SET NULL`), não
        apagadas -- antes o handler apagava todas à mão (`user_routes.py:140-142`).
        
        EXCEÇÃO CRÍTICA (AP-06): exige autenticação. Apenas admin ou o próprio
        usuário pode deletar a conta. A correção do CRITICAL prevalece sobre
        preservar o contrato original da rota.
        """
        user = self.get_user(user_id)
        caller = self.resolve_actor(actor)
        if not caller.is_admin and caller.id != user.id:
            raise Forbidden("Sem permissão para deletar este usuário")
        self._users.delete(user)
        self._users.commit()
        logger.info("Usuário deletado: %s", user_id)

    def resolve_actor(self, actor):
        """Usuário do token, ativo, ou `Unauthenticated`."""
        if actor is None:
            raise Unauthenticated("Autenticação necessária")
        user = self._users.get(actor.user_id)
        if user is None or not user.active:
            raise Unauthenticated("Token inválido")
        return user

    def _require_admin(self, actor, action):
        if not self.resolve_actor(actor).is_admin:
            raise Forbidden(f"Apenas administradores podem {action}")

    def _authorize_password_change(self, user, current_password, actor):
        caller = self.resolve_actor(actor)
        if caller.is_admin:
            return
        if caller.id != user.id:
            raise Forbidden("Sem permissão para alterar a senha deste usuário")
        if not current_password:
            raise InvalidInput("Senha atual é obrigatória")
        matches, _ = verify_password(current_password, user.password_hash)
        if not matches:
            raise Forbidden("Senha atual incorreta")

    def _check_password_policy(self, password):
        if len(password) < self._password_min_length:
            raise InvalidInput(f"Senha deve ter no mínimo {self._password_min_length} caracteres")
