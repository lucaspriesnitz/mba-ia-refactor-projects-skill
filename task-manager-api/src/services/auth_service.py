import logging

from ..errors import Forbidden, Unauthenticated
from ..security import hash_password, verify_password

logger = logging.getLogger(__name__)

INVALID_CREDENTIALS = "Credenciais inválidas"


class AuthService:
    def __init__(self, user_repository, token_service):
        self._users = user_repository
        self._tokens = token_service

    def login(self, email, password):
        """Retorna `(user, token)`. Mesma ordem de checagem do original:
        credencial (401) antes de status da conta (403)."""
        user = self._users.get_by_email(email)
        if user is None:
            raise Unauthenticated(INVALID_CREDENTIALS)

        matches, needs_rehash = verify_password(password, user.password_hash)
        if not matches:
            raise Unauthenticated(INVALID_CREDENTIALS)
        if needs_rehash:
            user.password_hash = hash_password(password)
            self._users.commit()
            logger.info("Hash de senha legado (MD5) regravado para o usuário %s", user.id)

        if not user.active:
            raise Forbidden("Usuário inativo")

        return user, self._tokens.issue(user)
