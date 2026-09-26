"""Hash de senha e emissão/validação de credencial (fecha AP-03 e a base do AP-06).

Antes: senha em texto puro no banco (`database.py:31, 76-78`), gravada crua no
cadastro (`models.py:126-129`) e comparada dentro do SQL (`models.py:110`) -- o
que também abria o bypass de login por injeção.

Nenhuma dependência nova: `werkzeug.security` (pbkdf2-sha256 com salt por
usuário) e `itsdangerous` já vêm com o Flask.
"""

import logging

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from werkzeug.security import check_password_hash, generate_password_hash

from ..models.errors import NaoAutenticado

logger = logging.getLogger(__name__)

METODO_DE_HASH = "pbkdf2:sha256"
SALT_DO_TOKEN = "autenticacao-loja"


class AuthService:
    def __init__(self, secret_key, token_ttl_segundos):
        self._serializador = URLSafeTimedSerializer(secret_key, salt=SALT_DO_TOKEN)
        self._token_ttl_segundos = token_ttl_segundos

    def gerar_hash_de_senha(self, senha):
        return generate_password_hash(senha, method=METODO_DE_HASH)

    def senha_confere(self, senha_informada, hash_armazenado):
        if not hash_armazenado or "$" not in hash_armazenado:
            # Registro anterior à refatoração, com senha em texto puro. Não
            # autenticamos e não comparamos: o usuário precisa redefinir a senha.
            logger.warning(
                "Credencial em formato legado (texto puro) encontrada; login recusado. "
                "Force a redefinição de senha para este usuário."
            )
            return False
        return check_password_hash(hash_armazenado, senha_informada)

    def emitir_token(self, usuario_id, papel):
        return self._serializador.dumps({"sub": usuario_id, "papel": papel})

    def validar_token(self, token):
        try:
            dados = self._serializador.loads(token, max_age=self._token_ttl_segundos)
        except SignatureExpired:
            raise NaoAutenticado("Credencial expirada")
        except BadSignature:
            raise NaoAutenticado("Credencial inválida")
        if not isinstance(dados, dict) or "sub" not in dados:
            raise NaoAutenticado("Credencial inválida")
        return dados
